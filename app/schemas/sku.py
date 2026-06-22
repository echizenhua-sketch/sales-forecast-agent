"""
SKU 相关 Schema
"""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import List


class SkuDetailResponse(BaseModel):
    """SKU 明细响应"""
    id: int
    task_id: int
    month: str
    product_name: str | None
    sku_code: str
    material_code: str | None
    business_unit: str | None = None
    product_series: str | None = None
    factory: str | None = None
    product_attribute: str | None = None
    product_category: str | None = None
    ex_factory_price: float | None = None
    launch_date: datetime | None = None

    # 库存与排产
    initial_inventory: float | None
    production_plan: float | None
    safety_stock: float | None
    total_supply: float | None

    # SAR 需求组成（v2.2：5个渠道）
    sar_province: float | None
    sar_dealer: float | None
    sar_ecommerce: float | None
    sar_ka: float | None
    sar_expansion: float | None
    sar_total: float | None

    # 缺口与满足率
    gap: float | None
    service_level: float | None

    # 可满足明细（v2.2：5个渠道）
    satisfied_province: float | None
    satisfied_dealer: float | None
    satisfied_ecommerce: float | None
    satisfied_ka: float | None
    satisfied_expansion: float | None
    satisfied_demand: float | None
    satisfied_ka_before_25: float | None = None

    # 未满足明细（v2.2：5个渠道）
    unsatisfied_province: float | None
    unsatisfied_dealer: float | None
    unsatisfied_ecommerce: float | None
    unsatisfied_ka: float | None
    unsatisfied_expansion: float | None
    unsatisfied_demand: float | None

    # 风险标识
    risk_level: str | None
    risk_reason: str | None
    risk_score: float | None

    created_at: datetime

    class Config:
        from_attributes = True


class SkuListResponse(BaseModel):
    """SKU 列表响应"""
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    items: List[SkuDetailResponse] = Field(..., description="SKU 列表")
