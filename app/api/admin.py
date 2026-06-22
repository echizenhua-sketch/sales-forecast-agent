"""
管理与辅助 API。
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.auth import get_optional_user
from app.db import get_db
from app.models.audit import AuditLog
from app.models.config import SystemConfig
from app.models.sku import SkuForecastDetail
from app.models.task import TaskFile
from app.models.user import User

router = APIRouter()


@router.get("/logs")
async def list_logs(
    limit: int = Query(default=50, ge=1, le=200),
    operation: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """查询操作日志。"""
    query = db.query(AuditLog)
    if operation:
        query = query.filter(AuditLog.operation == operation)
    rows = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit).all()
    return {
        "total": len(rows),
        "items": [
            {
                "id": row.id,
                "user_id": row.user_id,
                "username": row.username,
                "operation": row.operation,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "detail": json.loads(row.detail or "{}"),
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ],
    }


@router.get("/settings")
async def list_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """查询系统配置。"""
    rows = db.query(SystemConfig).order_by(SystemConfig.config_key.asc()).all()
    return {
        "items": [
            {
                "key": row.config_key,
                "value": row.config_value,
                "type": row.config_type,
                "description": row.description,
            }
            for row in rows
        ]
    }


@router.get("/notifications")
async def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """返回工作台通知。"""
    failed_count = db.query(TaskFile).filter(TaskFile.status == "FAILED").count()
    risk_count = db.query(SkuForecastDetail).filter(SkuForecastDetail.risk_level.in_(["CRITICAL", "HIGH"])).count()
    items = []
    if failed_count:
        items.append({"level": "warning", "title": "任务失败", "message": f"有 {failed_count} 个任务处理失败"})
    if risk_count:
        items.append({"level": "risk", "title": "高风险 SKU", "message": f"当前有 {risk_count} 个高风险 SKU 需要关注"})
    if not items:
        items.append({"level": "info", "title": "系统运行正常", "message": "暂无新的风险通知"})
    return {"items": items}


@router.get("/search")
async def global_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """全局搜索任务和 SKU。"""
    pattern = f"%{q}%"
    tasks = (
        db.query(TaskFile)
        .filter(or_(TaskFile.file_name.like(pattern), TaskFile.task_name.like(pattern)))
        .order_by(TaskFile.created_at.desc())
        .limit(limit)
        .all()
    )
    skus = (
        db.query(SkuForecastDetail)
        .filter(or_(SkuForecastDetail.sku_code.like(pattern), SkuForecastDetail.product_name.like(pattern)))
        .order_by(SkuForecastDetail.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "tasks": [
            {"id": row.id, "type": "task", "title": row.task_name or row.file_name, "status": row.status}
            for row in tasks
        ],
        "skus": [
            {
                "id": row.id,
                "task_id": row.task_id,
                "type": "sku",
                "title": row.sku_code,
                "description": row.product_name,
                "risk_level": row.risk_level,
            }
            for row in skus
        ],
    }
