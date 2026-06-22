"""
业务计算服务
=============

整合 Excel 解析、分配算法、风险评分等核心业务逻辑
"""

from decimal import Decimal
from typing import List, Dict, Any
import pandas as pd

from app.services.parser_service import ExcelParserService, ExcelParserError
from app.services.allocation_service import AllocationService
from app.services.risk_service import RiskCalculationService


class ForecastCalculationService:
    """预测计算服务"""

    def __init__(self):
        self.parser = ExcelParserService()
        self.allocator = AllocationService()
        self.risk_calculator = RiskCalculationService()

    def process_forecast_file(self, file_path: str) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        处理预测文件

        Args:
            file_path: Excel 文件路径

        Returns:
            (sku_details, summary)
            - sku_details: SKU 明细列表
            - summary: 汇总统计

        Raises:
            ExcelParserError: 解析失败
        """
        # 1. 解析 Excel 文件
        df, metadata = self.parser.parse_excel(file_path)

        # 2. 计算每个 SKU 的分配和风险
        sku_details = []
        for idx, row in df.iterrows():
            sku_detail = self._calculate_sku_detail(row)
            sku_details.append(sku_detail)

        # 3. 计算汇总统计
        summary = self._calculate_summary(sku_details, metadata)

        return sku_details, summary

    @staticmethod
    def _is_missing(value: Any) -> bool:
        """判断 pandas/Excel 空值，避免 NaN/NaT 直接进入数据库。"""
        if value is None:
            return True
        try:
            return bool(pd.isna(value))
        except (TypeError, ValueError):
            return False

    @classmethod
    def _clean_text(cls, value: Any) -> str:
        """清洗文本字段，保留 Excel 数字型 SKU 的可读编码。"""
        if cls._is_missing(value):
            return ""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    @classmethod
    def _clean_number(cls, value: Any, default: float = 0) -> Any:
        """清洗数值字段，把 Excel 空值转为默认值。"""
        if cls._is_missing(value) or value == "":
            return default
        return value

    @classmethod
    def _clean_date(cls, value: Any) -> Any:
        """清洗日期字段，把 pandas NaT 转为 None。"""
        if cls._is_missing(value):
            return None
        if hasattr(value, "to_pydatetime"):
            return value.to_pydatetime()
        return value

    def _calculate_sku_detail(self, row: pd.Series) -> Dict[str, Any]:
        """
        计算单个 SKU 的明细

        Args:
            row: DataFrame 行数据

        Returns:
            SKU 明细字典
        """
        # 提取基础数据
        total_supply = Decimal(str(self._clean_number(row.get("total_supply", 0))))
        sar_province = Decimal(str(self._clean_number(row.get("sar_province", 0))))
        sar_dealer = Decimal(str(self._clean_number(row.get("sar_dealer", 0))))
        sar_ecommerce = Decimal(str(self._clean_number(row.get("sar_ecommerce", 0))))
        sar_ka = Decimal(str(self._clean_number(row.get("sar_ka", 0))))
        sar_expansion = Decimal(str(self._clean_number(row.get("sar_expansion", 0))))
        sar_total = sar_province + sar_dealer + sar_ecommerce + sar_ka + sar_expansion
        gap = total_supply - sar_total

        # 计算可满足/未满足分配
        allocation = self.allocator.allocate_satisfied_unsatisfied(
            total_supply=total_supply,
            sar_province=sar_province,
            sar_dealer=sar_dealer,
            sar_ecommerce=sar_ecommerce,
            sar_ka=sar_ka,
            sar_expansion=sar_expansion,
        )

        # 计算满足率
        service_level = (allocation["satisfied"]["total"] / sar_total * 100) if sar_total > 0 else Decimal("100")

        # 计算风险
        risk_level, risk_reason, risk_score = self.risk_calculator.calculate_risk(
            total_supply=total_supply,
            sar_total=sar_total,
            gap=gap,
        )

        # 构造 SKU 明细
        sku_detail = {
            # 基础信息
            "sku_code": self._clean_text(row.get("sku_code", "")),
            "product_name": self._clean_text(row.get("product_name", "")),
            "material_code": self._clean_text(row.get("material_code", "")),
            "business_unit": self._clean_text(row.get("business_unit", "")),
            "product_series": self._clean_text(row.get("product_series", "")),
            "factory": self._clean_text(row.get("factory", "")),
            "product_attribute": self._clean_text(row.get("product_attribute", "")),
            "product_category": self._clean_text(row.get("product_category", "")),
            "ex_factory_price": float(self._clean_number(row.get("ex_factory_price", 0))),
            "launch_date": self._clean_date(row.get("launch_date")),

            # 库存与排产
            "initial_inventory": float(self._clean_number(row.get("initial_inventory", 0))),
            "production_plan": float(self._clean_number(row.get("production_plan", 0))),
            "safety_stock": float(self._clean_number(row.get("safety_stock", 0))),
            "total_supply": float(total_supply),

            # SAR 需求（5个渠道）
            "sar_province": float(sar_province),
            "sar_dealer": float(sar_dealer),
            "sar_ecommerce": float(sar_ecommerce),
            "sar_ka": float(sar_ka),
            "sar_expansion": float(sar_expansion),
            "sar_total": float(sar_total),

            # 缺口与满足率
            "gap": float(gap),
            "service_level": float(service_level),

            # 可满足明细（5个渠道）
            "satisfied_province": float(allocation["satisfied"]["province"]),
            "satisfied_dealer": float(allocation["satisfied"]["dealer"]),
            "satisfied_ecommerce": float(allocation["satisfied"]["ecommerce"]),
            "satisfied_ka": float(allocation["satisfied"]["ka"]),
            "satisfied_expansion": float(allocation["satisfied"]["expansion"]),
            "satisfied_demand": float(allocation["satisfied"]["total"]),
            "satisfied_ka_before_25": float(self._clean_number(row.get("satisfied_ka_before_25", 0))),

            # 未满足明细（5个渠道）
            "unsatisfied_province": float(allocation["unsatisfied"]["province"]),
            "unsatisfied_dealer": float(allocation["unsatisfied"]["dealer"]),
            "unsatisfied_ecommerce": float(allocation["unsatisfied"]["ecommerce"]),
            "unsatisfied_ka": float(allocation["unsatisfied"]["ka"]),
            "unsatisfied_expansion": float(allocation["unsatisfied"]["expansion"]),
            "unsatisfied_demand": float(allocation["unsatisfied"]["total"]),

            # 风险标识
            "risk_level": risk_level,
            "risk_reason": risk_reason,
            "risk_score": float(risk_score),
        }

        return sku_detail

    def _calculate_summary(self, sku_details: List[Dict[str, Any]], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        计算汇总统计

        Args:
            sku_details: SKU 明细列表
            metadata: 元数据

        Returns:
            汇总统计字典
        """
        if not sku_details:
            return {
                "total_supply": 0,
                "total_sar": 0,
                "total_gap": 0,
                "service_level": 0,
                "critical_risk_count": 0,
                "high_risk_count": 0,
                "medium_risk_count": 0,
            }

        # 汇总计算
        total_supply = sum(sku["total_supply"] for sku in sku_details)
        total_sar = sum(sku["sar_total"] for sku in sku_details)
        total_gap = total_supply - total_sar
        service_level = (sum(sku["satisfied_demand"] for sku in sku_details) / total_sar * 100) if total_sar > 0 else 100

        # 风险统计
        critical_risk_count = sum(1 for sku in sku_details if sku["risk_level"] == "CRITICAL")
        high_risk_count = sum(1 for sku in sku_details if sku["risk_level"] == "HIGH")
        medium_risk_count = sum(1 for sku in sku_details if sku["risk_level"] == "MEDIUM")

        return {
            "total_supply": total_supply,
            "total_sar": total_sar,
            "total_gap": total_gap,
            "service_level": service_level,
            "target_service_level": 98.0,
            "critical_risk_count": critical_risk_count,
            "high_risk_count": high_risk_count,
            "medium_risk_count": medium_risk_count,
        }
