"""
任务相关 Schema
"""

from datetime import datetime
from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    """创建任务请求"""
    task_name: str | None = Field(None, max_length=200, description="任务名称")


class TaskResponse(BaseModel):
    """任务响应"""
    id: int
    task_name: str | None
    file_name: str
    file_size: int
    status: str
    error_message: str | None
    progress: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskSummaryResponse(BaseModel):
    """汇总结果响应"""
    id: int
    task_id: int
    month: str
    total_supply: float | None
    total_sar: float | None
    total_gap: float | None
    service_level: float | None
    target_service_level: float
    inventory_turnover_days: float | None
    critical_risk_count: int
    high_risk_count: int
    medium_risk_count: int
    created_at: datetime

    class Config:
        from_attributes = True
