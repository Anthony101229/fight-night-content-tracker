"""Event endpoints: list/filter, detail with full card, and crew assignment."""

import datetime as dt
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import ColumnElement, select
from sqlalchemy.orm import selectinload

from app.db import DbSession
from app.models import Bout, CrewAssignment, CrewMember, Event
from app.schemas import CrewAssignmentCreate, CrewAssignmentOut, EventDetail, EventOut

router = APIRouter(prefix="/events", tags=["events"])

When = Literal["upcoming", "past"]


def event_filters(
    when: When | None, q: str | None, date_from: dt.date | None, date_to: dt.date | None
) -> list[ColumnElement[bool]]:
    """Build WHERE conditions shared by the events list and the footage summary."""
    conditions = []
    today = dt.date.today()
    if when == "upcoming":
        conditions.append(Event.date >= today)
    elif when == "past":
        conditions.append(Event.date < today)
    if q:
        conditions.append(Event.name.ilike(f"%{q}%"))
    if date_from:
        conditions.append(Event.date >= date_from)
    if date_to:
        conditions.append(Event.date <= date_to)
    return conditions


@router.get("", response_model=list[EventOut])
def list_events(
    db: DbSession,
    when: When | None = None,
    q: str | None = Query(None, description="Case-insensitive search on event name"),
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[Event]:
    """List events, newest first, with optional filters."""
    query = (
        select(Event)
        .where(*event_filters(when, q, date_from, date_to))
        .order_by(Event.date.desc(), Event.id)
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(query))


@router.get("/{event_id}", response_model=EventDetail)
def get_event(event_id: int, db: DbSession) -> Event:
    """One event with its fight card (fighters + footage) and crew assignments."""
    # selectinload fetches each related table in one extra query, instead of
    # one query per bout (the "N+1 query" problem).
    bouts = selectinload(Event.bouts)
    query = (
        select(Event)
        .where(Event.id == event_id)
        .options(
            bouts.selectinload(Bout.red_fighter),
            bouts.selectinload(Bout.blue_fighter),
            bouts.selectinload(Bout.footage),
            selectinload(Event.crew_assignments).selectinload(CrewAssignment.crew_member),
        )
    )
    event = db.scalar(query)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    return event


@router.post(
    "/{event_id}/crew", response_model=CrewAssignmentOut, status_code=status.HTTP_201_CREATED
)
def assign_crew(event_id: int, body: CrewAssignmentCreate, db: DbSession) -> CrewAssignment:
    """Assign a crew member to an event. Role defaults to the member's usual role."""
    if db.get(Event, event_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    member = db.get(CrewMember, body.crew_member_id)
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Crew member not found")
    if _find_assignment(db, event_id, member.id) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Crew member already assigned")

    assignment = CrewAssignment(
        event_id=event_id, crew_member=member, role=body.role or member.role
    )
    db.add(assignment)
    db.commit()
    return assignment


@router.delete("/{event_id}/crew/{crew_member_id}", status_code=status.HTTP_204_NO_CONTENT)
def unassign_crew(event_id: int, crew_member_id: int, db: DbSession) -> Response:
    """Remove a crew member from an event."""
    assignment = _find_assignment(db, event_id, crew_member_id)
    if assignment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")
    db.delete(assignment)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _find_assignment(db: DbSession, event_id: int, crew_member_id: int) -> CrewAssignment | None:
    return db.scalar(
        select(CrewAssignment).where(
            CrewAssignment.event_id == event_id,
            CrewAssignment.crew_member_id == crew_member_id,
        )
    )
