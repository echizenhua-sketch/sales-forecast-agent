"""FastAPI application entrypoint for the forecast agent MVP."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.core.config import get_settings
from src.services.ai_service import answer_question
from src.services.calc_service import TemplateError, build_summary, parse_forecast_file
from src.services.store import AppStore, User


class LoginRequest(BaseModel):
    """Login request payload."""

    username: str
    password: str


class ChatRequest(BaseModel):
    """AI chat request payload."""

    task_id: int
    session_id: str
    question: str


class ExportRequest(BaseModel):
    """Export request payload."""

    task_id: int
    export_type: str = "summary"
    export_format: str = "csv"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    store = AppStore(settings)
    app = FastAPI(title=settings.app_name)
    app.state.store = store
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:4173",
            "http://localhost:4173",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def get_store() -> AppStore:
        return app.state.store

    def current_user(
        authorization: Annotated[str | None, Header()] = None,
        app_store: AppStore = Depends(get_store),
    ) -> User:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="未登录或登录已过期")
        user = app_store.get_user_by_token(authorization.removeprefix("Bearer ").strip())
        if not user:
            raise HTTPException(status_code=401, detail="未登录或登录已过期")
        return user

    @app.get("/api/health")
    def health() -> dict[str, str]:
        """Return a simple health status payload."""
        return {"status": "ok", "app": settings.app_name}

    @app.post("/api/v1/auth/login")
    def login(payload: LoginRequest, app_store: AppStore = Depends(get_store)) -> dict[str, Any]:
        """Authenticate a user and return a bearer token."""
        user = app_store.authenticate(payload.username, payload.password)
        if not user:
            raise HTTPException(status_code=401, detail="账号或密码错误，请重试")
        token = app_store.create_session(user, settings.secret_key)
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "real_name": user.real_name,
            },
        }

    @app.get("/api/v1/auth/me")
    def me(user: User = Depends(current_user)) -> dict[str, Any]:
        """Return the current user."""
        return {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "real_name": user.real_name,
        }

    @app.post("/api/v1/files/upload")
    async def upload_file(
        file: UploadFile = File(...),
        user: User = Depends(current_user),
        app_store: AppStore = Depends(get_store),
    ) -> dict[str, Any]:
        """Upload, parse, calculate, and persist an Excel forecast file."""
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in {".xlsx", ".xls", ".csv"}:
            raise HTTPException(status_code=400, detail="仅支持 .xlsx / .xls / .csv 文件")
        file_bytes = await file.read()
        if len(file_bytes) > settings.max_upload_size_mb * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件大小不能超过 50MB")

        upload_path = app_store.upload_dir / f"{Path(file.filename or 'upload.xlsx').name}"
        upload_path.write_bytes(file_bytes)
        task_id = app_store.create_task(user, file.filename or upload_path.name, upload_path, file_bytes)
        try:
            rows = parse_forecast_file(str(upload_path))
            summary = build_summary(rows)
            app_store.insert_details(task_id, rows)
            app_store.upsert_summary(task_id, summary)
            app_store.finish_task(task_id)
            app_store.add_log(user, "UPLOAD", f"上传并解析文件：{file.filename}")
        except TemplateError as exc:
            app_store.fail_task(task_id, str(exc))
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            app_store.fail_task(task_id, "文件解析失败，请检查模板和数字字段。")
            raise HTTPException(status_code=400, detail="文件解析失败，请检查模板和数字字段。") from exc
        task = app_store.get_task(task_id)
        return {
            "task_id": task_id,
            "file_name": task["file_name"],
            "file_size": task["file_size"],
            "status": task["status"],
            "progress": task["progress"],
        }

    @app.get("/api/v1/tasks/recent")
    def recent_tasks(
        user: User = Depends(current_user),
        app_store: AppStore = Depends(get_store),
    ) -> dict[str, Any]:
        """Return recent forecast tasks."""
        return {"items": app_store.recent_tasks()}

    @app.get("/api/v1/tasks/{task_id}")
    def get_task(
        task_id: int,
        user: User = Depends(current_user),
        app_store: AppStore = Depends(get_store),
    ) -> dict[str, Any]:
        """Return task status and progress."""
        task = app_store.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        return {
            "task_id": task["id"],
            "status": task["status"],
            "progress": task["progress"],
            "eta_seconds": 0 if task["status"] == "SUCCESS" else 12,
            "error_message": task["error_message"],
            "file_name": task["file_name"],
            "file_size": task["file_size"],
            "created_at": task["created_at"],
        }

    @app.get("/api/v1/tasks/{task_id}/summary")
    def get_summary(
        task_id: int,
        user: User = Depends(current_user),
        app_store: AppStore = Depends(get_store),
    ) -> dict[str, Any]:
        """Return task KPI summary."""
        summary = app_store.get_summary(task_id)
        if not summary:
            raise HTTPException(status_code=404, detail="汇总结果不存在")
        return {"task_id": task_id, **summary}

    @app.get("/api/v1/tasks/{task_id}/details")
    def get_details(
        task_id: int,
        risk_level: str | None = None,
        sku_code: str | None = None,
        sort_by: str = "sku_code",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 50,
        user: User = Depends(current_user),
        app_store: AppStore = Depends(get_store),
    ) -> dict[str, Any]:
        """Return paginated SKU details."""
        total, rows = app_store.get_details(
            task_id=task_id,
            risk_level=risk_level,
            sku_code=sku_code,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
        return {"total": total, "page": page, "page_size": page_size, "items": rows}

    @app.get("/api/v1/tasks/{task_id}/skus/{sku_code}")
    def get_sku(
        task_id: int,
        sku_code: str,
        user: User = Depends(current_user),
        app_store: AppStore = Depends(get_store),
    ) -> dict[str, Any]:
        """Return one SKU calculation detail."""
        sku = app_store.get_sku(task_id, sku_code)
        if not sku:
            raise HTTPException(status_code=404, detail="SKU 不存在")
        return sku

    @app.post("/api/v1/ai/chat")
    def chat(
        payload: ChatRequest,
        user: User = Depends(current_user),
        app_store: AppStore = Depends(get_store),
    ) -> dict[str, Any]:
        """Answer a question based on task data."""
        if not app_store.get_task(payload.task_id):
            raise HTTPException(status_code=404, detail="任务不存在")
        response = answer_question(app_store, payload.task_id, payload.question)
        app_store.save_conversation(
            user=user,
            task_id=payload.task_id,
            session_id=payload.session_id,
            question=payload.question,
            answer=response["answer"],
            references=response["references"],
            response_type=response["type"],
        )
        app_store.add_log(user, "AI_CHAT", f"AI 问答：{payload.question}")
        return response

    @app.post("/api/v1/export")
    def create_export(
        payload: ExportRequest,
        user: User = Depends(current_user),
        app_store: AppStore = Depends(get_store),
    ) -> dict[str, Any]:
        """Create a report export file."""
        _, rows = app_store.get_details(payload.task_id, page_size=100000)
        if not rows:
            raise HTTPException(status_code=404, detail="没有可导出的明细数据")
        export_format = payload.export_format.lower()
        if export_format not in {"csv", "md"}:
            raise HTTPException(status_code=400, detail="当前支持 csv / md 导出")
        result = app_store.create_export(
            user=user,
            task_id=payload.task_id,
            export_type=payload.export_type,
            export_format=export_format,
            rows=rows,
        )
        app_store.add_log(user, "EXPORT", f"导出任务 {payload.task_id} 报表")
        return result

    @app.get("/api/v1/export/{export_id}")
    def get_export(
        export_id: int,
        user: User = Depends(current_user),
        app_store: AppStore = Depends(get_store),
    ) -> dict[str, Any]:
        """Return export generation status."""
        export = app_store.get_export(export_id)
        if not export:
            raise HTTPException(status_code=404, detail="导出记录不存在")
        return {"export_id": export_id, "status": "SUCCESS", **export}

    @app.get("/api/v1/export/{export_id}/download")
    def download_export(
        export_id: int,
        user: User = Depends(current_user),
        app_store: AppStore = Depends(get_store),
    ) -> FileResponse:
        """Download an export file."""
        export = app_store.get_export(export_id)
        if not export:
            raise HTTPException(status_code=404, detail="导出记录不存在")
        return FileResponse(export["file_path"], filename=export["file_name"])

    @app.get("/api/v1/logs")
    def list_logs(
        page: int = 1,
        page_size: int = 50,
        user: User = Depends(current_user),
        app_store: AppStore = Depends(get_store),
    ) -> dict[str, Any]:
        """Return audit log entries."""
        total, rows = app_store.list_logs(page=page, page_size=page_size)
        return {"total": total, "page": page, "page_size": page_size, "items": rows}

    return app


app = create_app()
