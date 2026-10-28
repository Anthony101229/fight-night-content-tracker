"""SQLAlchemy 2.0 models for the Fight Night Content Tracker."""

import datetime as dt
from enum import StrEnum

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Predictable constraint names, so Alembic migrations can refer to them later.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base class for all models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class CardPosition(StrEnum):
    MAIN = "main"
    CO_MAIN = "co_main"
    PRELIM = "prelim"


class CrewRole(StrEnum):
    CAMERA = "camera"
    PRODUCER = "producer"
    EDITOR = "editor"


class FootageStatus(StrEnum):
    PLANNED = "planned"
    SHOT = "shot"
    EDITED = "edited"
    DELIVERED = "delivered"


def pg_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    """Postgres enum type that stores the lowercase values ("planned"), not the names ("PLANNED")."""
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


# One shared type object, because crew_members and crew_assignments both use it.
crew_role_enum = pg_enum(CrewRole, "crew_role")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    date: Mapped[dt.date] = mapped_column(index=True)
    location: Mapped[str | None] = mapped_column(String(200))
    # Unique: the scraper uses this to recognise an event it has already saved.
    source_url: Mapped[str] = mapped_column(String(500), unique=True)

    bouts: Mapped[list["Bout"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )
    crew_assignments: Mapped[list["CrewAssignment"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class Fighter(Base):
    __tablename__ = "fighters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    nickname: Mapped[str | None] = mapped_column(String(120))
    record: Mapped[str | None] = mapped_column(String(20))  # e.g. "27-1-0"
    weight_class: Mapped[str | None] = mapped_column(String(50))
    # Names aren't unique (two fighters can share one), so the scraper matches on URL.
    source_url: Mapped[str] = mapped_column(String(500), unique=True)


class Bout(Base):
    __tablename__ = "bouts"
    __table_args__ = (
        # The same two fighters can't appear twice on one event's card.
        UniqueConstraint("event_id", "red_fighter_id", "blue_fighter_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    red_fighter_id: Mapped[int] = mapped_column(ForeignKey("fighters.id"))
    blue_fighter_id: Mapped[int] = mapped_column(ForeignKey("fighters.id"))
    weight_class: Mapped[str | None] = mapped_column(String(50))
    card_position: Mapped[CardPosition] = mapped_column(
        pg_enum(CardPosition, "card_position")
    )
    # Result fields stay empty until the fight happens.
    result: Mapped[str | None] = mapped_column(String(50))
    method: Mapped[str | None] = mapped_column(String(100))
    round: Mapped[int | None]

    event: Mapped[Event] = relationship(back_populates="bouts")
    # Two foreign keys point at fighters, so each relationship says which one it uses.
    red_fighter: Mapped[Fighter] = relationship(foreign_keys=[red_fighter_id])
    blue_fighter: Mapped[Fighter] = relationship(foreign_keys=[blue_fighter_id])
    footage: Mapped["FootageAsset | None"] = relationship(
        back_populates="bout", cascade="all, delete-orphan"
    )


class CrewMember(Base):
    __tablename__ = "crew_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[CrewRole] = mapped_column(crew_role_enum)  # their usual role

    assignments: Mapped[list["CrewAssignment"]] = relationship(
        back_populates="crew_member", cascade="all, delete-orphan"
    )


class CrewAssignment(Base):
    __tablename__ = "crew_assignments"
    __table_args__ = (UniqueConstraint("event_id", "crew_member_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True
    )
    crew_member_id: Mapped[int] = mapped_column(
        ForeignKey("crew_members.id", ondelete="CASCADE")
    )
    role: Mapped[CrewRole] = mapped_column(crew_role_enum)  # their role at this event

    event: Mapped[Event] = relationship(back_populates="crew_assignments")
    crew_member: Mapped[CrewMember] = relationship(back_populates="assignments")


class FootageAsset(Base):
    __tablename__ = "footage_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    # unique=True makes this one-to-one: each bout has exactly one footage record.
    bout_id: Mapped[int] = mapped_column(
        ForeignKey("bouts.id", ondelete="CASCADE"), unique=True
    )
    status: Mapped[FootageStatus] = mapped_column(
        pg_enum(FootageStatus, "footage_status"),
        default=FootageStatus.PLANNED,
        server_default=FootageStatus.PLANNED.value,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    bout: Mapped[Bout] = relationship(back_populates="footage")
