"""Database engine and session factory setup."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from src.core.config import settings


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    """Create the parent directory for file-backed SQLite databases."""
    url = make_url(database_url)
    database_path = url.database

    if not url.drivername.startswith("sqlite") or not database_path:
        return

    if database_path == ":memory:":
        return

    sqlite_path = Path(database_path)
    if not sqlite_path.is_absolute():
        sqlite_path = Path.cwd() / sqlite_path

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_dir(settings.database_url)
engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)
