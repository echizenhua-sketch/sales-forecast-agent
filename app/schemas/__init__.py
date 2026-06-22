"""
Pydantic Schemas - 数据传输对象
================================

用于 API 请求/响应的数据验证和序列化
"""

from app.schemas.user import UserLogin, UserResponse, UserCreate
from app.schemas.task import TaskCreate, TaskResponse, TaskSummaryResponse
from app.schemas.sku import SkuDetailResponse, SkuListResponse
from app.schemas.ai import ChatRequest, ChatResponse
from app.schemas.export import ExportRequest, ExportResponse

__all__ = [
    "UserLogin",
    "UserResponse",
    "UserCreate",
    "TaskCreate",
    "TaskResponse",
    "TaskSummaryResponse",
    "SkuDetailResponse",
    "SkuListResponse",
    "ChatRequest",
    "ChatResponse",
    "ExportRequest",
    "ExportResponse",
]
