"""Seed demo crew members: python -m app.seed

These are made-up people so the dashboard has crew to assign. Safe to run repeatedly.
"""

from sqlalchemy import select

from app.db import SessionLocal
from app.models import CrewMember, CrewRole

DEMO_CREW = [
    ("Maya Torres", CrewRole.CAMERA),
    ("Jordan Lee", CrewRole.CAMERA),
    ("Chris Okafor", CrewRole.CAMERA),
    ("Priya Shah", CrewRole.PRODUCER),
    ("Sam Rivera", CrewRole.PRODUCER),
    ("Alex Kim", CrewRole.EDITOR),
    ("Taylor Brooks", CrewRole.EDITOR),
]


def seed_crew() -> int:
    """Add any demo crew member that isn't already in the database. Returns how many were added."""
    added = 0
    with SessionLocal() as session:
        for name, role in DEMO_CREW:
            if session.scalar(select(CrewMember).where(CrewMember.name == name)) is None:
                session.add(CrewMember(name=name, role=role))
                added += 1
        session.commit()
    return added


if __name__ == "__main__":
    added = seed_crew()
    print(f"Added {added} crew members ({len(DEMO_CREW) - added} already existed)")
