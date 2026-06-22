"""Shared pytest fixtures for the forecast agent API."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch) -> TestClient:
    """Create an isolated API test client backed by temp project data."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{(tmp_path / 'app.db').as_posix()}")
    monkeypatch.setenv("DATA_DIR", (tmp_path / "data").as_posix())

    from src.api.app import create_app

    app = create_app()
    return TestClient(app)


@pytest.fixture()
def auth_headers(client: TestClient) -> dict[str, str]:
    """Authenticate the demo planner account and return bearer headers."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "planner", "password": "planner123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def sample_excel(tmp_path: Path) -> Path:
    """Create a valid forecast workbook with the required sheet and columns."""
    import pandas as pd

    path = tmp_path / "forecast.xlsx"
    frame = pd.DataFrame(
        [
            {
                "月份": "2024-05",
                "产品名称": "无线耳机 A",
                "SKU 编码": "SKU-001",
                "4月30日库存": 1000,
                "5月排产": 500,
                "安全库存预留": 100,
                "省大区SAR": 400,
                "网络经销商SAR": 300,
                "海外出口SAR": 200,
                "内部调拨需求": 100,
            },
            {
                "月份": "2024-05",
                "产品名称": "无线耳机 B",
                "SKU 编码": "SKU-002",
                "4月30日库存": 100,
                "5月排产": 100,
                "安全库存预留": 50,
                "省大区SAR": 500,
                "网络经销商SAR": 400,
                "海外出口SAR": 200,
                "内部调拨需求": 100,
            },
        ]
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        frame.to_excel(writer, sheet_name="预测及排期明细表", index=False)
    return path
