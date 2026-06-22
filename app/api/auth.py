"""
认证 API
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
import bcrypt

from app.core.auth import create_access_token
from app.db import get_db
from app.models.user import User
from app.schemas.user import UserLogin, UserResponse
from app.services.audit_service import write_audit_log

router = APIRouter()


@router.post("/auth/login", response_model=dict)
async def login(credentials: UserLogin, request: Request, db: Session = Depends(get_db)):
    """
    用户登录

    Args:
        credentials: 登录凭证
        db: 数据库会话

    Returns:
        登录结果和用户信息
    """
    # 查询用户
    user = db.query(User).filter(User.username == credentials.username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 验证密码
    if not bcrypt.checkpw(
        credentials.password.encode('utf-8'),
        user.password_hash.encode('utf-8')
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    # 检查用户状态
    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用"
        )

    write_audit_log(
        db,
        operation="LOGIN",
        user=user,
        resource_type="USER",
        resource_id=user.id,
        detail={"username": user.username},
        request=request,
    )
    db.commit()

    token = create_access_token(user)
    return {
        "success": True,
        "message": "登录成功",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "role": user.role,
            "department": user.department,
        }
    }


@router.post("/auth/logout")
async def logout():
    """
    用户登出

    Returns:
        登出结果
    """
    return {
        "success": True,
        "message": "登出成功"
    }
