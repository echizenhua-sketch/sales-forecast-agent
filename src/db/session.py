"""Database engine and session factory setup."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.config import settings


engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)
