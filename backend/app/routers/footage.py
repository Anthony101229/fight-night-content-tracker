"""Footage endpoints: update one bout's status, and a per-event summary."""

import datetime as dt

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.db import DbSession
from app.models import Bout, Event, FootageAsset, FootageStatus
from app.routers.events import When, event_filters
from app.schemas import FootageOut, FootageSummary, FootageUpdate

router = APIRouter(tags=["footage"])


@router.patch("/bouts/{bout_id}/footage", response_model=FootageOut)
def update_footage(bout_id: int, body: FootageUpdate, db: DbSession) -> FootageAsset:
    """Change a bout's footage status and/or notes. Fields you leave out are unchanged."""
    bout = db.get(Bout, bout_id)
    if bout is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Bout not found")
    if bout.footage is None:
        bout.footage = FootageAsset()

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(bout.footage, field, value)
    db.commit()
    return bout.footage


@router.get("/footage/summary", response_model=list[FootageSummary])
def footage_summary(
    db: DbSession,
    when: When | None = None,
    q: str | None = None,
    date_from: dt.date | None = None,
    date_to: dt.date | None = None,
) -> list[FootageSummary]:
    """Count bouts in each footage status, per event. Takes the same filters as GET /events."""
    status_counts = [
        func.count(FootageAsset.id).filter(FootageAsset.status == s).label(s.value)
        for s in FootageStatus
    ]
    # Outer joins keep events that have no bouts yet (their counts are 0).
    query = (
        select(
            Event.id,
            Event.name,
            Event.date,
            func.count(FootageAsset.id).label("total"),
            *status_counts,
        )
        .outerjoin(Bout, Bout.event_id == Event.id)
        .outerjoin(FootageAsset, FootageAsset.bout_id == Bout.id)
        .where(*event_filters(when, q, date_from, date_to))
        .group_by(Event.id)
        .order_by(Event.date.desc(), Event.id)
    )
    return [
        FootageSummary(
            event_id=row.id,
            event_name=row.name,
            event_date=row.date,
            total=row.total,
            planned=row.planned,
            shot=row.shot,
            edited=row.edited,
            delivered=row.delivered,
            pending=row.total - row.delivered,
        )
        for row in db.execute(query)
    ]
