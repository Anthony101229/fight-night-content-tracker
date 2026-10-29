"""Tests for listing crew and assigning/unassigning them to events."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import CrewMember, CrewRole
from tests.factories import make_event


def test_list_crew_members(client: TestClient, crew_member: CrewMember) -> None:
    response = client.get("/crew-members")

    assert response.status_code == 200
    assert response.json() == [{"id": crew_member.id, "name": "Maya Torres", "role": "camera"}]


def test_assign_crew_defaults_to_members_role(
    client: TestClient, db: Session, crew_member: CrewMember
) -> None:
    event = make_event(db)

    response = client.post(f"/events/{event.id}/crew", json={"crew_member_id": crew_member.id})

    assert response.status_code == 201
    assert response.json()["role"] == "camera"
    assert response.json()["crew_member"]["name"] == "Maya Torres"
    detail = client.get(f"/events/{event.id}").json()
    assert [a["crew_member"]["id"] for a in detail["crew_assignments"]] == [crew_member.id]


def test_assign_crew_with_a_different_role(
    client: TestClient, db: Session, crew_member: CrewMember
) -> None:
    event = make_event(db)

    response = client.post(
        f"/events/{event.id}/crew",
        json={"crew_member_id": crew_member.id, "role": CrewRole.PRODUCER},
    )

    assert response.json()["role"] == "producer"


def test_assigning_twice_returns_409(
    client: TestClient, db: Session, crew_member: CrewMember
) -> None:
    event = make_event(db)
    url = f"/events/{event.id}/crew"

    client.post(url, json={"crew_member_id": crew_member.id})
    response = client.post(url, json={"crew_member_id": crew_member.id})

    assert response.status_code == 409


def test_assign_unknown_crew_member_returns_404(client: TestClient, db: Session) -> None:
    event = make_event(db)

    response = client.post(f"/events/{event.id}/crew", json={"crew_member_id": 999999})

    assert response.status_code == 404
    assert response.json()["detail"] == "Crew member not found"


def test_assign_to_unknown_event_returns_404(client: TestClient, crew_member: CrewMember) -> None:
    response = client.post("/events/999999/crew", json={"crew_member_id": crew_member.id})

    assert response.status_code == 404
    assert response.json()["detail"] == "Event not found"


def test_unassign_crew(client: TestClient, db: Session, crew_member: CrewMember) -> None:
    event = make_event(db)
    client.post(f"/events/{event.id}/crew", json={"crew_member_id": crew_member.id})

    response = client.delete(f"/events/{event.id}/crew/{crew_member.id}")

    assert response.status_code == 204
    assert client.get(f"/events/{event.id}").json()["crew_assignments"] == []


def test_unassign_when_not_assigned_returns_404(
    client: TestClient, db: Session, crew_member: CrewMember
) -> None:
    event = make_event(db)

    response = client.delete(f"/events/{event.id}/crew/{crew_member.id}")

    assert response.status_code == 404
