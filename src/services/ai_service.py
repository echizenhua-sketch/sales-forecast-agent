"""Rule-first AI question answering service for forecast task data."""

from __future__ import annotations

import re
from typing import Any

from src.services.store import AppStore


BOUNDARY_KEYWORDS = ["竞争对手", "市场占有率", "供应商评估", "外部市场", "股价"]


def answer_question(store: AppStore, task_id: int, question: str) -> dict[str, Any]:
    """Answer a user question from persisted task data."""
    if any(keyword in question for keyword in BOUNDARY_KEYWORDS):
        return {
            "answer": (
                "抱歉，当前系统仅支持基于已上传数据的产销平衡分析，"
                "无法回答外部市场预测、竞争对手分析或供应商评估类问题。\n\n"
                "我可以帮你查询 SKU 缺口、风险等级、SAR 组成和排产优先级。"
            ),
            "references": [],
            "type": "boundary_reject",
        }

    sku_match = re.search(r"(SKU[-_ ]?\d+)", question, re.IGNORECASE)
    if sku_match:
        sku_code = sku_match.group(1).replace("_", "-").replace(" ", "-").upper()
        sku = store.get_sku(task_id, sku_code)
        if not sku:
            return {
                "answer": f"未找到 {sku_code} 的数据，请检查 SKU 编码是否正确。",
                "references": [],
                "type": "rule_engine",
            }
        return {
            "answer": (
                f"**{sku['sku_code']}（{sku['product_name']}）** 的供应缺口为 "
                f"{sku['gap']:+,.0f}。\n\n"
                f"- 总供应：{sku['total_supply']:,.0f}\n"
                f"- 合计 SAR：{sku['sar_total']:,.0f}\n"
                f"- 满足率：{sku['service_level']:.2f}%\n"
                f"- 风险等级：{sku['risk_label']}\n\n"
                f"{sku['risk_reason']}"
            ),
            "references": [
                {
                    "table": "库存风险明细清单",
                    "sku": sku["sku_code"],
                    "row": sku["row_index"],
                }
            ],
            "type": "rule_engine",
        }

    if "高风险" in question or "优先排产" in question or "缺货风险" in question:
        _, rows = store.get_details(task_id, sort_by="gap", sort_order="asc", page_size=5)
        risky = [row for row in rows if row["risk_level"] in {"CRITICAL", "HIGH"}]
        lines = [
            f"{index}. {row['sku_code']}（{row['product_name']}）：缺口 {row['gap']:+,.0f}，{row['risk_label']}"
            for index, row in enumerate(risky, start=1)
        ]
        return {
            "answer": "建议优先关注以下 SKU：\n\n" + "\n".join(lines),
            "references": [
                {"table": "库存风险明细清单", "sku": row["sku_code"], "row": row["row_index"]}
                for row in risky
            ],
            "type": "rule_engine",
        }

    summary = store.get_summary(task_id)
    if summary and ("总供应" in question or "总缺口" in question or "满足率" in question):
        return {
            "answer": (
                f"当前任务总供应为 {summary['total_supply']:,.0f}，"
                f"合计 SAR 为 {summary['total_sar']:,.0f}，"
                f"总缺口为 {summary['total_gap']:+,.0f}，"
                f"满足率为 {summary['service_level']:.2f}%。"
            ),
            "references": [{"table": "预测及排期汇总表", "task_id": task_id}],
            "type": "rule_engine",
        }

    return {
        "answer": (
            "已基于当前任务数据完成初步分析。你可以继续询问某个 SKU 的缺口、"
            "哪些 SKU 需要优先排产，或总供应、总缺口和满足率。"
        ),
        "references": [{"table": "预测及排期汇总表", "task_id": task_id}],
        "type": "rule_engine",
    }
