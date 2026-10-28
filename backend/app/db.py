"""Database engine and session factory."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

engine = create_engine(settings.database_url)

# expire_on_commit=False keeps loaded attributes usable after commit,
# which is handy when returning objects from API endpoints.
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
