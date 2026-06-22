"""
任务相关模型
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, BigInteger, Integer, Text, ForeignKey, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class TaskFile(Base):
    """文件任务表"""

    __tablename__ = "task_file"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    task_name: Mapped[str | None] = mapped_column(String(200), comment="任务名称")
    file_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="文件名")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="文件存储路径")
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="文件大小（字节）")
    file_md5: Mapped[str | None] = mapped_column(String(32), comment="文件MD5校验值")
    upload_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_user.id"), nullable=False, comment="上传用户ID")
    status: Mapped[str] = mapped_column(String(20), nullable=False, comment="状态: UPLOADING, PARSING, CALCULATING, SUCCESS, FAILED")
    error_message: Mapped[str | None] = mapped_column(Text, comment="错误信息")
    progress: Mapped[int] = mapped_column(Integer, default=0, comment="进度(0-100)")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def __repr__(self):
        return f"<TaskFile(id={self.id}, file_name={self.file_name}, status={self.status})>"


class TaskSummary(Base):
    """汇总结果表"""

    __tablename__ = "task_summary"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("task_file.id", ondelete="CASCADE"), unique=True, nullable=False, comment="任务ID")
    month: Mapped[str] = mapped_column(String(7), nullable=False, comment="月份（格式: 2024-05）")

    # 汇总指标
    total_supply: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="总供应")
    total_sar: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="合计SAR")
    total_gap: Mapped[Decimal | None] = mapped_column(DECIMAL(18, 2), comment="总缺口 (= 总供应 - 合计SAR)")
    service_level: Mapped[Decimal | None] = mapped_column(DECIMAL(5, 2), comment="满足率(%)")
    target_service_level: Mapped[Decimal] = mapped_column(DECIMAL(5, 2), default=Decimal("98.00"), comment="目标满足率（默认98%）")
    inventory_turnover_days: Mapped[Decimal | None] = mapped_column(DECIMAL(5, 1), comment="库存周转天数")

    # 风险统计
    critical_risk_count: Mapped[int] = mapped_column(Integer, default=0, comment="极高风险数量")
    high_risk_count: Mapped[int] = mapped_column(Integer, default=0, comment="高风险数量")
    medium_risk_count: Mapped[int] = mapped_column(Integer, default=0, comment="中风险数量")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    def __repr__(self):
        return f"<TaskSummary(id={self.id}, task_id={self.task_id}, month={self.month})>"
