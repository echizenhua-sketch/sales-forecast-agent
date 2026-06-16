"""FastAPI application entrypoint."""

from fastapi import FastAPI

from src.core.config import settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title=settings.app_name)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        """Return a simple health status payload."""
        return {"status": "ok"}

    return app


app = create_app()
