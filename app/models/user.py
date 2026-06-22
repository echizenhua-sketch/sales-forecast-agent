"""
用户模型
"""

from datetime import datetime
from sqlalchemy import String, DateTime, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """用户表"""

    __tablename__ = "sys_user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="用户名")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希（bcrypt）")
    real_name: Mapped[str | None] = mapped_column(String(100), comment="真实姓名")
    role: Mapped[str] = mapped_column(String(20), nullable=False, comment="角色: ADMIN, MANAGER, PLANNER, ANALYST")
    department: Mapped[str | None] = mapped_column(String(100), comment="部门")
    email: Mapped[str | None] = mapped_column(String(100), comment="邮箱")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", comment="状态: ACTIVE, INACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"
