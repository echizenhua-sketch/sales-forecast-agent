"""
轻量会话认证工具。

当前项目是内网 MVP，使用签名 token 承载用户身份，避免继续在业务接口中硬编码 user_id。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from typing import Any

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import get_db
from app.models.user import User


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(payload: str) -> str:
    settings = get_settings()
    digest = hmac.new(settings.secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).digest()
    return _b64encode(digest)


def create_access_token(user: User) -> str:
    """生成签名访问 token。"""
    settings = get_settings()
    expires_at = datetime.utcnow() + timedelta(hours=settings.session_expire_hours)
    payload: dict[str, Any] = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "exp": int(expires_at.timestamp()),
    }
    payload_part = _b64encode(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    return f"{payload_part}.{_sign(payload_part)}"


def decode_access_token(token: str) -> dict[str, Any]:
    """校验并解析访问 token。"""
    try:
        payload_part, signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效登录凭证") from exc

    if not hmac.compare_digest(_sign(payload_part), signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录凭证校验失败")

    try:
        payload = json.loads(_b64decode(payload_part).decode("utf-8"))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录凭证解析失败") from exc

    if int(payload.get("exp", 0)) < int(datetime.utcnow().timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期")
    return payload


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """从 Authorization 头读取当前用户。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")

    payload = decode_access_token(authorization.removeprefix("Bearer ").strip())
    user = db.query(User).filter(User.id == payload.get("user_id")).first()
    if not user or user.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return user


def get_optional_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """
    兼容旧静态页的可选认证。

    新前端会传 token；旧页面或测试未传时回退到 admin/首个 ACTIVE 用户，避免一次性破坏现有链路。
    """
    if authorization and authorization.startswith("Bearer "):
        return get_current_user(authorization=authorization, db=db)

    user = (
        db.query(User)
        .filter(User.status == "ACTIVE")
        .order_by(User.id.asc())
        .first()
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先初始化用户")
    return user
