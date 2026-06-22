"""
操作审计日志服务。
"""

from __future__ import annotations

import json
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User


def write_audit_log(
    db: Session,
    *,
    operation: str,
    user: User | None = None,
    resource_type: str | None = None,
    resource_id: int | None = None,
    detail: dict[str, Any] | None = None,
    request: Request | None = None,
) -> AuditLog:
    """写入一条操作日志。"""
    entry = AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else None,
        operation=operation,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=json.dumps(detail or {}, ensure_ascii=False),
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent")[:500] if request else None,
    )
    db.add(entry)
    db.flush()
    return entry
