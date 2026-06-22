"""
审计日志和导出记录模型
"""

from datetime import datetime
from sqlalchemy import String, DateTime, BigInteger, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    """操作日志表"""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, comment="主键ID")
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sys_user.id", ondelete="SET NULL"), comment="用户ID")
    username: Mapped[str | None] = mapped_column(String(50), comment="用户名")
    operation: Mapped[str] = mapped_column(String(50), nullable=False, comment="操作类型（LOGIN, UPLOAD, EXPORT, DELETE, AI_CHAT等）")
    resource_type: Mapped[str | None] = mapped_column(String(50), comment="资源类型（TASK, FILE, REPORT等）")
    resource_id: Mapped[int | None] = mapped_column(BigInteger, comment="资源ID")
    detail: Mapped[str | None] = mapped_column(Text, comment="详细信息（JSON格式）")
    ip_address: Mapped[str | None] = mapped_column(String(45), comment="IP地址（支持IPv6）")
    user_agent: Mapped[str | None] = mapped_column(String(500), comment="User Agent")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, operation={self.operation}, username={self.username})>"


class ExportRecord(Base):
    """导出记录表"""

    __tablename__ = "export_record"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, comment="主键ID")
    task_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("task_file.id", ondelete="SET NULL"), comment="任务ID")
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_user.id"), nullable=False, comment="用户ID")
    export_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="导出类型（SUMMARY, SKU_DETAIL, AI_CONVERSATION等）")
    export_format: Mapped[str] = mapped_column(String(10), nullable=False, comment="导出格式（XLSX, CSV, PDF）")
    file_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="文件名")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="文件路径")
    file_size: Mapped[int | None] = mapped_column(BigInteger, comment="文件大小（字节）")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    def __repr__(self):
        return f"<ExportRecord(id={self.id}, file_name={self.file_name}, export_type={self.export_type})>"
