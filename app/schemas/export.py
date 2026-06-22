"""
导出相关 Schema
"""

from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    """导出请求"""
    task_id: int = Field(..., description="任务ID")
    export_type: str = Field(default="SKU_DETAIL", description="导出类型: SUMMARY, SKU_DETAIL, AI_CONVERSATION")
    export_format: str = Field(default="XLSX", description="导出格式: XLSX, CSV, PDF")


class ExportResponse(BaseModel):
    """导出响应"""
    export_id: int = Field(..., description="导出记录ID")
    file_name: str = Field(..., description="文件名")
    file_path: str = Field(..., description="文件路径")
    file_size: int | None = Field(None, description="文件大小（字节）")
    download_url: str = Field(..., description="下载URL")
