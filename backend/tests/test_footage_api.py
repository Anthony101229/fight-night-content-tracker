"""Tests for updating footage status and the per-event footage summary."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CardPosition
from tests.factories import make_event


def test_update_footage_status(client: TestClient, db: Session) -> None:
    event = make_event(db)
    bout_id = event.bouts[0].id

    response = client.patch(f"/bouts/{bout_id}/footage", json={"status": "shot"})

    assert response.status_code == 200
    assert response.json()["status"] == "shot"
    detail = client.get(f"/events/{event.id}").json()
    assert detail["bouts"][0]["footage"]["status"] == "shot"


def test_partial_update_keeps_other_fields(client: TestClient, db: Session) -> None:
    bout_id = make_event(db).bouts[0].id
    url = f"/bouts/{bout_id}/footage"

    client.patch(url, json={"status": "edited", "notes": "Needs color grade"})
    response = client.patch(url, json={"notes": "Graded"})  # status not sent

    assert response.json()["status"] == "edited"
    assert response.json()["notes"] == "Graded"


def test_invalid_status_returns_422(client: TestClient, db: Session) -> None:
    bout_id = make_event(db).bouts[0].id

    response = client.patch(f"/bouts/{bout_id}/footage", json={"status": "uploaded"})

    assert response.status_code == 422


def test_null_status_returns_422(client: TestClient, db: Session) -> None:
    bout_id = make_event(db).bouts[0].id

    response = client.patch(f"/bouts/{bout_id}/footage", json={"status": None})

    assert response.status_code == 422


def test_update_footage_for_missing_bout_returns_404(client: TestClient) -> None:
    response = client.patch("/bouts/999999/footage", json={"status": "shot"})

    assert response.status_code == 404


def test_footage_summary_counts_each_status(client: TestClient, db: Session) -> None:
    event = make_event(
        db, positions=(CardPosition.MAIN, CardPosition.CO_MAIN, CardPosition.PRELIM)
    )
    main, co_main, _prelim = event.bouts
    client.patch(f"/bouts/{main.id}/footage", json={"status": "delivered"})
    client.patch(f"/bouts/{co_main.id}/footage", json={"status": "edited"})

    response = client.get("/footage/summary")

    assert response.status_code == 200
    assert response.json() == [
        {
            "event_id": event.id,
            "event_name": "UFC Test Night",
            "event_date": str(event.date),
            "total": 3,
            "planned": 1,
            "shot": 0,
            "edited": 1,
            "delivered": 1,
            "pending": 2,
        }
    ]


def test_footage_summary_includes_events_without_bouts(client: TestClient, db: Session) -> None:
    make_event(db, name="UFC Empty Card", positions=())

    summary = client.get("/footage/summary").json()

    assert summary[0]["event_name"] == "UFC Empty Card"
    assert summary[0]["total"] == 0
    assert summary[0]["pending"] == 0


def test_footage_summary_uses_event_filters(client: TestClient, db: Session) -> None:
    make_event(db, name="UFC Past", days_from_today=-30)
    make_event(db, name="UFC Future", days_from_today=30)

    summary = client.get("/footage/summary", params={"when": "past"}).json()

    assert [row["event_name"] for row in summary] == ["UFC Past"]
