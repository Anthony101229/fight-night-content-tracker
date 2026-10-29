"""Tests for listing, filtering and fetching events."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CardPosition
from tests.factories import make_event


def test_list_events_newest_first(client: TestClient, db: Session) -> None:
    make_event(db, name="UFC Past", days_from_today=-30)
    make_event(db, name="UFC Future", days_from_today=30)

    response = client.get("/events")

    assert response.status_code == 200
    assert [e["name"] for e in response.json()] == ["UFC Future", "UFC Past"]


def test_filter_upcoming_and_past(client: TestClient, db: Session) -> None:
    make_event(db, name="UFC Past", days_from_today=-30)
    make_event(db, name="UFC Future", days_from_today=30)

    upcoming = client.get("/events", params={"when": "upcoming"}).json()
    past = client.get("/events", params={"when": "past"}).json()

    assert [e["name"] for e in upcoming] == ["UFC Future"]
    assert [e["name"] for e in past] == ["UFC Past"]


def test_search_by_name_is_case_insensitive(client: TestClient, db: Session) -> None:
    make_event(db, name="UFC 400")
    make_event(db, name="UFC Fight Night London", days_from_today=14)

    response = client.get("/events", params={"q": "london"})

    assert [e["name"] for e in response.json()] == ["UFC Fight Night London"]


def test_filter_by_date_range(client: TestClient, db: Session) -> None:
    early = make_event(db, name="UFC Early", days_from_today=5)
    make_event(db, name="UFC Late", days_from_today=50)

    response = client.get(
        "/events", params={"date_from": str(early.date), "date_to": str(early.date)}
    )

    assert [e["name"] for e in response.json()] == ["UFC Early"]


def test_invalid_filter_is_rejected(client: TestClient) -> None:
    assert client.get("/events", params={"when": "someday"}).status_code == 422


def test_get_event_returns_card_in_running_order(client: TestClient, db: Session) -> None:
    # Created out of order on purpose: the API should sort main event first, prelims last.
    event = make_event(
        db,
        positions=(
            CardPosition.PRELIM,
            CardPosition.MAIN,
            CardPosition.MAIN_CARD,
            CardPosition.CO_MAIN,
        ),
    )

    response = client.get(f"/events/{event.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "UFC Test Night"
    assert [b["card_position"] for b in body["bouts"]] == ["main", "co_main", "main_card", "prelim"]
    first = body["bouts"][0]
    assert first["red_fighter"]["name"] == "UFC Test Night Red 1"
    assert first["footage"]["status"] == "planned"
    assert body["crew_assignments"] == []


def test_get_missing_event_returns_404(client: TestClient) -> None:
    response = client.get("/events/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Event not found"}
