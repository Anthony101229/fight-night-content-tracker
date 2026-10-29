"""Pydantic models: the shapes of API requests and responses.

These are separate from the database models so the API's public contract
doesn't change every time a table does.
"""

import datetime as dt

from pydantic import BaseModel, ConfigDict, field_validator

from app.models import CardPosition, CrewRole, FootageStatus


class ORMModel(BaseModel):
    """Base for response models that are built from SQLAlchemy objects."""

    model_config = ConfigDict(from_attributes=True)


class FighterOut(ORMModel):
    """A fighter as returned by the API."""

    id: int
    name: str
    nickname: str | None
    record: str | None
    weight_class: str | None


class FootageOut(ORMModel):
    """A bout's footage status and notes."""

    bout_id: int
    status: FootageStatus
    notes: str | None
    updated_at: dt.datetime


class BoutOut(ORMModel):
    """One bout with both fighters, the result, and footage status."""

    id: int
    weight_class: str | None
    card_position: CardPosition
    red_fighter: FighterOut
    blue_fighter: FighterOut
    result: str | None
    method: str | None
    round: int | None
    footage: FootageOut | None


class CrewMemberOut(ORMModel):
    """A crew member as returned by the API."""

    id: int
    name: str
    role: CrewRole


class CrewAssignmentOut(ORMModel):
    """A crew member assigned to an event."""

    id: int
    role: CrewRole
    crew_member: CrewMemberOut


class EventOut(ORMModel):
    """An event without its card (used in lists)."""

    id: int
    name: str
    date: dt.date
    location: str | None
    source_url: str


class EventDetail(EventOut):
    """An event with its full fight card and crew assignments."""

    bouts: list[BoutOut]
    crew_assignments: list[CrewAssignmentOut]


class CrewAssignmentCreate(BaseModel):
    """Request body for assigning a crew member to an event."""

    crew_member_id: int
    role: CrewRole | None = None  # defaults to the crew member's usual role


class FootageUpdate(BaseModel):
    """Partial update: only the fields you send are changed."""

    status: FootageStatus | None = None
    notes: str | None = None

    @field_validator("status")
    @classmethod
    def status_not_null(cls, value: FootageStatus | None) -> FootageStatus:
        """Reject an explicit null status (the database column is NOT NULL).

        Runs only when "status" is actually sent, so leaving it out is still allowed.
        """
        if value is None:
            raise ValueError("status cannot be null")
        return value


class FootageSummary(BaseModel):
    """Bout counts per footage status for one event."""

    event_id: int
    event_name: str
    event_date: dt.date
    total: int
    planned: int
    shot: int
    edited: int
    delivered: int
    pending: int  # everything not yet delivered
