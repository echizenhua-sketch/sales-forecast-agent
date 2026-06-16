"""Health and database smoke tests."""

from sqlalchemy import text

from src.db.session import SessionLocal, engine


def test_health_endpoint_returns_ok(client) -> None:
    """Health endpoint should return a simple OK payload."""
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_engine_and_session_connect_with_default_sqlite() -> None:
    """Default SQLite engine and session should execute a trivial query."""
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1

    with SessionLocal() as session:
        assert session.execute(text("SELECT 1")).scalar_one() == 1
