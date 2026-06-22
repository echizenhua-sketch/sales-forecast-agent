"""End-to-end MVP API tests for the forecast agent."""


def test_health_endpoint_returns_ok(client) -> None:
    """Health endpoint should expose service status."""
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_rejects_invalid_password(client) -> None:
    """Login should reject bad credentials with a client error."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "planner", "password": "bad-password"},
    )

    assert response.status_code == 401


def test_upload_parse_calculate_query_chat_export_and_logs(
    client, auth_headers, sample_excel
) -> None:
    """Core flow should match the development checklist MVP chain."""
    with sample_excel.open("rb") as file_obj:
        upload_response = client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files={
                "file": (
                    sample_excel.name,
                    file_obj,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

    assert upload_response.status_code == 200
    task_id = upload_response.json()["task_id"]
    assert upload_response.json()["status"] == "SUCCESS"

    task_response = client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers)
    assert task_response.status_code == 200
    assert task_response.json()["progress"] == 100

    summary_response = client.get(
        f"/api/v1/tasks/{task_id}/summary", headers=auth_headers
    )
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["total_supply"] == 1550
    assert summary["total_sar"] == 2200
    assert summary["total_gap"] == -650

    details_response = client.get(
        f"/api/v1/tasks/{task_id}/details?risk_level=CRITICAL",
        headers=auth_headers,
    )
    assert details_response.status_code == 200
    details = details_response.json()
    assert details["total"] == 1
    assert details["items"][0]["sku_code"] == "SKU-002"

    sku_response = client.get(
        f"/api/v1/tasks/{task_id}/skus/SKU-002", headers=auth_headers
    )
    assert sku_response.status_code == 200
    assert sku_response.json()["sar_total"] == 1200

    chat_response = client.post(
        "/api/v1/ai/chat",
        headers=auth_headers,
        json={
            "task_id": task_id,
            "session_id": "pytest-session",
            "question": "SKU-002 的缺口是多少？",
        },
    )
    assert chat_response.status_code == 200
    assert "SKU-002" in chat_response.json()["answer"]
    assert chat_response.json()["references"][0]["sku"] == "SKU-002"

    boundary_response = client.post(
        "/api/v1/ai/chat",
        headers=auth_headers,
        json={
            "task_id": task_id,
            "session_id": "pytest-session",
            "question": "预测竞争对手市场占有率",
        },
    )
    assert boundary_response.status_code == 200
    assert boundary_response.json()["type"] == "boundary_reject"

    export_response = client.post(
        "/api/v1/export",
        headers=auth_headers,
        json={"task_id": task_id, "export_type": "summary", "export_format": "csv"},
    )
    assert export_response.status_code == 200
    export_id = export_response.json()["export_id"]

    download_response = client.get(
        f"/api/v1/export/{export_id}/download", headers=auth_headers
    )
    assert download_response.status_code == 200
    assert "SKU-001" in download_response.text

    logs_response = client.get("/api/v1/logs", headers=auth_headers)
    assert logs_response.status_code == 200
    operations = {entry["operation"] for entry in logs_response.json()["items"]}
    assert {"LOGIN", "UPLOAD", "AI_CHAT", "EXPORT"}.issubset(operations)


def test_upload_rejects_invalid_template(client, auth_headers, tmp_path) -> None:
    """Parser should return a clear message for missing required sheet."""
    import pandas as pd

    invalid_path = tmp_path / "invalid.xlsx"
    pd.DataFrame([{"SKU 编码": "SKU-001"}]).to_excel(invalid_path, index=False)

    with invalid_path.open("rb") as file_obj:
        response = client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files={"file": (invalid_path.name, file_obj, "application/vnd.ms-excel")},
        )

    assert response.status_code == 400
    assert "预测及排期明细表" in response.json()["detail"]


def test_upload_accepts_csv_template(client, auth_headers, tmp_path) -> None:
    """CSV uploads should use the same required columns and calculation path."""
    csv_path = tmp_path / "forecast.csv"
    csv_path.write_text(
        "\n".join(
            [
                "月份,产品名称,SKU 编码,月度需求,4月30日库存,5月排产,安全库存预留,网络经销商SAR,海外出口SAR,内部调拨需求",
                "2024-05,蓝牙音箱 A,SKU-010,100,60,80,10,20,10,0",
            ]
        ),
        encoding="utf-8-sig",
    )

    with csv_path.open("rb") as file_obj:
        response = client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files={"file": (csv_path.name, file_obj, "text/csv")},
        )

    assert response.status_code == 200
    task_id = response.json()["task_id"]
    summary = client.get(f"/api/v1/tasks/{task_id}/summary", headers=auth_headers).json()
    assert summary["total_supply"] == 130
    assert summary["total_sar"] == 130
