"""Database engine, session factory, and the FastAPI session dependency."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url)

# expire_on_commit=False keeps loaded attributes usable after commit,
# which is handy when returning objects from API endpoints.
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Give each request its own session, closed when the request finishes."""
    with SessionLocal() as session:
        yield session


# Use as an endpoint parameter type: `def endpoint(db: DbSession): ...`
DbSession = Annotated[Session, Depends(get_db)]
