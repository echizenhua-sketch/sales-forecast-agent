"""Database engine and session factory setup."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import sessionmaker

from src.core.config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
settings = globals().get("settings") or get_settings()


def _normalize_sqlite_database_url(database_url: str) -> str:
    """Resolve relative SQLite database paths against the project root."""
    url = make_url(database_url)
    database_path = url.database

    if not url.drivername.startswith("sqlite") or not database_path:
        return database_url

    if database_path == ":memory:":
        return database_url

    sqlite_path = Path(database_path)
    if not sqlite_path.is_absolute():
        sqlite_path = (PROJECT_ROOT / sqlite_path).resolve()

    normalized_url = URL.create(
        drivername=url.drivername,
        username=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        database=sqlite_path.as_posix(),
        query=url.query,
    )
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    return normalized_url.render_as_string(hide_password=False)


engine = create_engine(_normalize_sqlite_database_url(settings.database_url), future=True)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)
