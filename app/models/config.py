"""
系统配置模型
"""

from datetime import datetime
from sqlalchemy import String, DateTime, BigInteger, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SystemConfig(Base):
    """系统配置表"""

    __tablename__ = "system_config"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True, comment="主键ID")
    config_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="配置键")
    config_value: Mapped[str | None] = mapped_column(Text, comment="配置值")
    config_type: Mapped[str | None] = mapped_column(String(20), comment="配置类型（STRING, NUMBER, JSON等）")
    description: Mapped[str | None] = mapped_column(String(500), comment="配置描述")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def __repr__(self):
        return f"<SystemConfig(id={self.id}, config_key={self.config_key})>"
