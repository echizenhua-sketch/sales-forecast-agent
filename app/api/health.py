"""
健康检查 API
"""

from fastapi import APIRouter
from app.db import check_db_connection

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    健康检查接口

    Returns:
        健康状态
    """
    db_status = check_db_connection()

    return {
        "status": "healthy" if db_status else "unhealthy",
        "database": "connected" if db_status else "disconnected",
    }
