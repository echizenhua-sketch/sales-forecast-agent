"""Test fixtures for API endpoint tests."""

import pytest
from fastapi.testclient import TestClient
from src.api.app import create_app


@pytest.fixture()
def client() -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(create_app())
