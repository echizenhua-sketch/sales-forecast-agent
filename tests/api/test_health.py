"""Health endpoint tests."""


def test_health_endpoint_returns_ok(client) -> None:
    """Health endpoint should return a simple OK payload."""
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
