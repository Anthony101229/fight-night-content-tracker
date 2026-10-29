"""Crew member endpoints."""

from fastapi import APIRouter
from sqlalchemy import select

from app.db import DbSession
from app.models import CrewMember
from app.schemas import CrewMemberOut

router = APIRouter(prefix="/crew-members", tags=["crew"])


@router.get("", response_model=list[CrewMemberOut])
def list_crew_members(db: DbSession) -> list[CrewMember]:
    """All crew members, for the assignment dropdown."""
    return list(db.scalars(select(CrewMember).order_by(CrewMember.role, CrewMember.name)))
