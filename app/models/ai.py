"""
AI 会话模型
"""

from datetime import datetime
from sqlalchemy import String, DateTime, BigInteger, Integer, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AIConversation(Base):
    """AI 会话表"""

    __tablename__ = "ai_conversation"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
        comment="主键ID",
    )
    task_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("task_file.id", ondelete="SET NULL"), comment="任务ID")
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("sys_user.id"), nullable=False, comment="用户ID")
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="会话ID（用于多轮对话）")
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="问题")
    answer: Mapped[str] = mapped_column(Text, nullable=False, comment="回答")
    context: Mapped[dict | None] = mapped_column(JSON, comment="上下文信息（JSON格式）")
    reference: Mapped[dict | None] = mapped_column(JSON, comment='引用数据（JSON格式，如 {"table": "...", "sku": "...", "row": 1}）')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    def __repr__(self):
        return f"<AIConversation(id={self.id}, session_id={self.session_id})>"
