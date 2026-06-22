"""
产销预测智能工作台 - ORM 模型
================================

版本：v2.2
创建日期：2026-06-21

包含模型：
- User: 用户表
- TaskFile: 文件任务表
- SkuForecastDetail: SKU 预测明细表（v2.2 版本，37 个字段）
- TaskSummary: 汇总结果表
- AIConversation: AI 会话表
- AuditLog: 操作日志表
- ExportRecord: 导出记录表
- SystemConfig: 系统配置表
"""

from app.models.base import Base
from app.models.user import User
from app.models.task import TaskFile, TaskSummary
from app.models.sku import SkuForecastDetail
from app.models.ai import AIConversation
from app.models.audit import AuditLog, ExportRecord
from app.models.config import SystemConfig

__all__ = [
    "Base",
    "User",
    "TaskFile",
    "TaskSummary",
    "SkuForecastDetail",
    "AIConversation",
    "AuditLog",
    "ExportRecord",
    "SystemConfig",
]
