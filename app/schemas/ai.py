"""
AI 对话相关 Schema
"""

from pydantic import BaseModel, Field
from typing import Dict, Any


class ChatRequest(BaseModel):
    """AI 对话请求"""
    task_id: int = Field(..., description="任务ID")
    session_id: str = Field(..., min_length=1, max_length=64, description="会话ID")
    question: str = Field(..., min_length=1, description="用户问题")


class ChatResponse(BaseModel):
    """AI 对话响应"""
    answer: str = Field(..., description="AI 回答")
    references: Dict[str, Any] | None = Field(None, description="引用数据")
    response_type: str = Field(default="text", description="响应类型: text, table, chart")
