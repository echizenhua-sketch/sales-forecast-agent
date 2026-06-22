"""Health and database smoke tests."""

import importlib
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import text

from src.db import session as session_module


def test_database_engine_and_session_use_project_anchored_temp_sqlite(
    monkeypatch, tmp_path
) -> None:
    """Reloaded session module should use a temp SQLite file without touching the default DB."""
    project_root = Path(__file__).resolve().parents[2]
    isolated_cwd = tmp_path / "isolated-cwd"
    isolated_cwd.mkdir()
    original_database_url = session_module.settings.database_url

    with TemporaryDirectory(dir=project_root) as temp_dir:
        temp_db_path = Path(temp_dir) / "smoke.db"
        relative_temp_db_path = temp_db_path.relative_to(project_root)
        reloaded_session = None

        try:
            monkeypatch.setattr(
                session_module.settings,
                "database_url",
                f"sqlite:///./{relative_temp_db_path.as_posix()}",
            )
            monkeypatch.chdir(isolated_cwd)

            reloaded_session = importlib.reload(session_module)

            assert Path(reloaded_session.engine.url.database).resolve() == temp_db_path.resolve()

            with reloaded_session.engine.connect() as connection:
                assert connection.execute(text("SELECT 1")).scalar_one() == 1

            with reloaded_session.SessionLocal() as session:
                assert session.execute(text("SELECT 1")).scalar_one() == 1

            assert temp_db_path.exists()
        finally:
            if reloaded_session is not None:
                reloaded_session.engine.dispose()
            session_module.settings.database_url = original_database_url
            importlib.reload(session_module)
