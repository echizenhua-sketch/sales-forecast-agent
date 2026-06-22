"""
SKU 预测明细模型（v2.2 版本）
=============================

包含 37 个核心字段：
- 6 个 SAR 字段（5 个渠道 + total）
- 6 个可满足明细字段
- 6 个未满足明细字段
- 3 个风险字段（level, reason, score）
- 4 个库存字段
- 12 个其他字段
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, BigInteger, Text, ForeignKey, DECIMAL, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SkuForecastDetail(Base):
    """SKU 预测明细表（v2.2 修正版）"""

    __tablename__ = "sku_forecast_detail"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("task_file.id", ondelete="CASCADE"), nullable=False, comment="任务ID")
    month: Mapped[str] = mapped_column(String(7), nullable=False, comment="月份（格式: 2024-05）")
    product_name: Mapped[str | None] = mapped_column(String(200), comment="产品名称")
    sku_code: Mapped[str] = mapped_column(String(100), nullable=False, comment="SKU编码")
    material_code: Mapped[str | None] = mapped_column(String(100), comment="物料编码")
    business_unit: Mapped[str | None] = mapped_column(String(100), comment="事业部")
    product_series: Mapped[str | None] = mapped_column(String(100), comment="产品系列")
    factory: Mapped[str | None] = mapped_column(String(100), comment="生产工厂")
    product_attribute: Mapped[str | None] = mapped_column(String(100), comment="属性")
    product_category: Mapped[str | None] = mapped_column(String(100), comment="产品类别")
    ex_factory_price: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="出厂价")
    launch_date: Mapped[datetime | None] = mapped_column(DateTime, comment="上市日期")

    # ============================================================
    # 库存与排产
    # ============================================================
    initial_inventory: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="期初库存（4月30日库存）")
    production_plan: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="排产计划（5月排产）")
    safety_stock: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="安全库存")
    total_supply: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="总供应 (= 期初库存 + 排产计划 - 安全库存预留)")

    # ============================================================
    # SAR 需求组成（v2.2 修正：5个独立渠道）
    # ============================================================
    sar_province: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="省大区SAR")
    sar_dealer: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="网络经销商SAR")
    sar_ecommerce: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="电商直营SAR")
    sar_ka: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="KA部SAR")
    sar_expansion: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="拓展部SAR")
    sar_total: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="合计SAR (= 省大区 + 网络经销商 + 电商直营 + KA部 + 拓展部)")

    # ============================================================
    # 缺口与满足率
    # ============================================================
    gap: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="SAR差异 (= 总供应 - 合计SAR)，负数表示缺货")
    service_level: Mapped[Decimal | None] = mapped_column(DECIMAL(5, 2), comment="满足率(%) (= 可满足合计 / 合计SAR * 100)")

    # ============================================================
    # 可满足明细（v2.2 新增：5个渠道独立统计）
    # ============================================================
    satisfied_province: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="省大区可满足")
    satisfied_dealer: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="网络经销商可满足")
    satisfied_ecommerce: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="电商直营可满足")
    satisfied_ka: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="KA部可满足")
    satisfied_expansion: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="拓展部可满足")
    satisfied_demand: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="可满足合计 (= 5个渠道可满足之和)")
    satisfied_ka_before_25: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="KA-5月25日前可满足（含25日）")

    # ============================================================
    # 未满足明细（v2.2 新增：5个渠道独立统计）
    # ============================================================
    unsatisfied_province: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="省大区未满足")
    unsatisfied_dealer: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="网络经销商未满足")
    unsatisfied_ecommerce: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="电商直营未满足")
    unsatisfied_ka: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="KA部未满足")
    unsatisfied_expansion: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="拓展部未满足")
    unsatisfied_demand: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="未满足合计 (= 5个渠道未满足之和)")

    # ============================================================
    # 风险标识（v2.2 修正：新增 risk_score 用于排序）
    # ============================================================
    risk_level: Mapped[str | None] = mapped_column(String(20), comment="风险等级: CRITICAL, HIGH, MEDIUM, NORMAL, OVERSTOCK, SUFFICIENT")
    risk_reason: Mapped[str | None] = mapped_column(Text, comment="风险原因（详细说明）")
    risk_score: Mapped[Decimal | None] = mapped_column(DECIMAL(5, 2), comment="风险评分（用于排序，数值越大风险越高，范围: 0-200）")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    # 索引设计
    __table_args__ = (
        Index("idx_task_month", "task_id", "month"),
        Index("idx_sku", "sku_code"),
        Index("idx_risk", "risk_level"),
        Index("idx_task_risk", "task_id", "risk_level"),
        Index("idx_task_score", "task_id", "risk_score"),
    )

    def __repr__(self):
        return f"<SkuForecastDetail(id={self.id}, sku_code={self.sku_code}, risk_level={self.risk_level})>"
