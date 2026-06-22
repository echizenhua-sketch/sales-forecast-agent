"""
FastAPI 应用主文件
==================

产销预测智能工作台 API 服务
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.db import check_db_connection
from app.api import admin, auth, tasks, health
from app.scripts.ensure_mysql_schema import ensure_schema

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时检查数据库连接
    print("=" * 60)
    print(f"{settings.app_name} - 启动中...")
    print("=" * 60)

    if check_db_connection():
        print("[OK] 数据库连接成功")
        changed = ensure_schema()
        if changed:
            print(f"[OK] 数据库兼容列已补齐: {len(changed)}")
    else:
        print("[ERROR] 数据库连接失败")

    print("=" * 60)
    yield

    # 关闭时清理资源
    print("应用正在关闭...")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    description="产销预测智能工作台 API",
    version="2.2.0",
    lifespan=lifespan,
)

# 配置 CORS
# 注意：当 allow_credentials=True 时不能用 ["*"]，需用正则匹配所有来源（含 file:// 的 null origin）
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",  # 匹配所有来源，兼容 file:// (null origin)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, prefix=settings.api_prefix, tags=["健康检查"])
app.include_router(auth.router, prefix=settings.api_prefix, tags=["认证"])
app.include_router(tasks.router, prefix=settings.api_prefix, tags=["任务管理"])
app.include_router(admin.router, prefix=settings.api_prefix, tags=["管理"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "app": settings.app_name,
        "version": "2.2.0",
        "status": "running",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
