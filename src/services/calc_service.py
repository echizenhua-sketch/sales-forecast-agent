"""Forecast calculation service for SKU-level SAR analysis."""

from __future__ import annotations

from typing import Any

import pandas as pd


REQUIRED_SHEET = "预测及排期明细表"
REQUIRED_COLUMNS = {"SKU 编码", "月度需求"}
NUMERIC_COLUMNS = {
    "4月30日库存": "initial_inventory",
    "5月排产": "production_plan",
    "安全库存预留": "safety_stock",
    "省大区SAR": "sar_province",
    "网络经销商SAR": "sar_dealer",
    "海外出口SAR": "sar_export",
    "内部调拨需求": "sar_internal",
}


class TemplateError(ValueError):
    """Raised when an uploaded workbook does not match the required template."""


def parse_forecast_file(path: str) -> list[dict[str, Any]]:
    """Parse and calculate a forecast workbook.

    Args:
        path: Local Excel file path.

    Returns:
        Calculated SKU rows ready for persistence.

    Raises:
        TemplateError: If the workbook does not contain required sheets or columns.
    """
    if path.lower().endswith(".csv"):
        frame = pd.read_csv(path, encoding="utf-8-sig")
    else:
        excel = pd.ExcelFile(path)
        if REQUIRED_SHEET not in excel.sheet_names:
            raise TemplateError("未找到《预测及排期明细表》Sheet，请检查文件格式后重新上传。")
        frame = pd.read_excel(path, sheet_name=REQUIRED_SHEET)
    if "SKU 编码" not in frame.columns:
        raise TemplateError("缺少必填列：SKU 编码。")

    frame = frame.copy()
    if "月度需求" in frame.columns and "省大区SAR" not in frame.columns:
        frame["省大区SAR"] = frame["月度需求"]

    missing = [column for column in NUMERIC_COLUMNS if column not in frame.columns]
    for column in missing:
        frame[column] = 0
    if "产品名称" not in frame.columns:
        frame["产品名称"] = frame["SKU 编码"]
    if "月份" not in frame.columns:
        frame["月份"] = "2024-05"

    if frame["SKU 编码"].isna().any():
        raise TemplateError("SKU 编码不能为空。")

    for column in NUMERIC_COLUMNS:
        frame[column] = pd.to_numeric(frame[column], errors="raise").fillna(0)

    frame["total_supply"] = (
        frame["4月30日库存"] + frame["5月排产"] - frame["安全库存预留"]
    )
    frame["sar_total"] = (
        frame["省大区SAR"]
        + frame["网络经销商SAR"]
        + frame["海外出口SAR"]
        + frame["内部调拨需求"]
    )
    frame["gap"] = frame["total_supply"] - frame["sar_total"]
    frame["satisfied_demand"] = frame[["total_supply", "sar_total"]].min(axis=1).clip(lower=0)
    frame["unsatisfied_demand"] = (frame["sar_total"] - frame["satisfied_demand"]).clip(
        lower=0
    )
    frame["service_level"] = (
        frame["satisfied_demand"] / frame["sar_total"].replace(0, pd.NA) * 100
    ).fillna(100)

    rows: list[dict[str, Any]] = []
    for index, row in frame.iterrows():
        risk_level, risk_label, risk_reason = classify_risk(
            gap=float(row["gap"]),
            sar_total=float(row["sar_total"]),
        )
        rows.append(
            {
                "month": str(row["月份"]),
                "product_name": str(row["产品名称"]),
                "sku_code": str(row["SKU 编码"]),
                "initial_inventory": float(row["4月30日库存"]),
                "production_plan": float(row["5月排产"]),
                "safety_stock": float(row["安全库存预留"]),
                "total_supply": float(row["total_supply"]),
                "sar_province": float(row["省大区SAR"]),
                "sar_dealer": float(row["网络经销商SAR"]),
                "sar_export": float(row["海外出口SAR"]),
                "sar_internal": float(row["内部调拨需求"]),
                "sar_total": float(row["sar_total"]),
                "gap": float(row["gap"]),
                "satisfied_demand": float(row["satisfied_demand"]),
                "unsatisfied_demand": float(row["unsatisfied_demand"]),
                "service_level": round(float(row["service_level"]), 2),
                "risk_level": risk_level,
                "risk_label": risk_label,
                "risk_reason": risk_reason,
                "row_index": int(index) + 2,
            }
        )
    return rows


def build_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build task-level KPI summary from calculated SKU rows."""
    total_supply = sum(row["total_supply"] for row in rows)
    total_sar = sum(row["sar_total"] for row in rows)
    total_gap = total_supply - total_sar
    satisfied = sum(row["satisfied_demand"] for row in rows)
    service_level = round((satisfied / total_sar * 100) if total_sar else 100, 2)
    initial_inventory = sum(row["initial_inventory"] for row in rows)
    daily_sar = total_sar / 30 if total_sar else 0
    risk_counts: dict[str, int] = {}
    for row in rows:
        risk_counts[row["risk_level"].lower()] = (
            risk_counts.get(row["risk_level"].lower(), 0) + 1
        )
    return {
        "month": rows[0]["month"] if rows else "2024-05",
        "total_supply": round(total_supply, 2),
        "total_sar": round(total_sar, 2),
        "total_gap": round(total_gap, 2),
        "service_level": service_level,
        "target_service_level": 98.0,
        "inventory_turnover_days": round((initial_inventory / daily_sar) if daily_sar else 0, 1),
        "risk_counts": risk_counts,
    }


def classify_risk(gap: float, sar_total: float) -> tuple[str, str, str]:
    """Classify risk using the PRD temporary thresholds."""
    ratio = (gap / sar_total * 100) if sar_total else 0
    if gap < -10000 or ratio < -30:
        return "CRITICAL", "极高风险", "缺口超过 30% 或绝对缺口过大，需紧急排产。"
    if -30 <= ratio < -15:
        return "HIGH", "缺货风险", "供应低于需求 15%-30%，需优先关注。"
    if -15 <= ratio < -5:
        return "MEDIUM", "中风险", "供应略低于需求，建议持续监控。"
    if ratio > 30:
        return "SUFFICIENT", "充足", "供应明显高于需求，当前库存较充足。"
    if ratio > 15:
        return "OVERSTOCK", "压货风险", "供应高于需求 15%，需关注库存积压。"
    return "NORMAL", "正常", "供需处于可接受平衡区间。"
