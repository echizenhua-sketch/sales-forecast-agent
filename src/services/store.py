"""SQLite-backed repository for forecast agent MVP data."""

from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.core.config import Settings


DEMO_USERS = {
    "planner": {
        "id": 1,
        "username": "planner",
        "password": "planner123",
        "role": "PLANNER",
        "real_name": "陈计划",
    },
    "admin": {
        "id": 2,
        "username": "admin",
        "password": "admin123",
        "role": "ADMIN",
        "real_name": "管理员",
    },
}


@dataclass(frozen=True)
class User:
    """Authenticated user context."""

    id: int
    username: str
    role: str
    real_name: str


class AppStore:
    """Small repository layer used by the MVP API.

    The implementation is deliberately SQLite-backed so the whole demo can run
    locally without MySQL, while preserving the same task/detail/export concepts.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.project_root = Path(__file__).resolve().parents[2]
        self.data_dir = self._resolve_data_dir(settings.data_dir)
        self.upload_dir = self.data_dir / "uploads"
        self.export_dir = self.data_dir / "exports"
        self.tmp_dir = self.data_dir / "tmp"
        for directory in (self.upload_dir, self.export_dir, self.tmp_dir):
            directory.mkdir(parents=True, exist_ok=True)
        self.db_path = self._resolve_sqlite_path(settings.database_url)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self._seed_users()

    def _resolve_data_dir(self, data_dir: Path) -> Path:
        """Resolve data directories without escaping the configured path."""
        if data_dir.is_absolute():
            return data_dir
        return (self.project_root / data_dir).resolve()

    def _resolve_sqlite_path(self, database_url: str) -> Path:
        """Resolve a SQLite URL to an on-disk database path."""
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            return self.data_dir / "app.db"
        raw_path = database_url[len(prefix) :]
        path = Path(raw_path)
        if path.is_absolute():
            return path
        return (self.project_root / path).resolve()

    def connect(self) -> sqlite3.Connection:
        """Open a row-friendly SQLite connection."""
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        """Create tables needed by the MVP flow."""
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password TEXT NOT NULL,
                    role TEXT NOT NULL,
                    real_name TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_md5 TEXT NOT NULL,
                    upload_user_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    progress INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sku_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    month TEXT NOT NULL,
                    product_name TEXT,
                    sku_code TEXT NOT NULL,
                    initial_inventory REAL NOT NULL,
                    production_plan REAL NOT NULL,
                    safety_stock REAL NOT NULL,
                    total_supply REAL NOT NULL,
                    sar_province REAL NOT NULL,
                    sar_dealer REAL NOT NULL,
                    sar_export REAL NOT NULL,
                    sar_internal REAL NOT NULL,
                    sar_total REAL NOT NULL,
                    gap REAL NOT NULL,
                    satisfied_demand REAL NOT NULL,
                    unsatisfied_demand REAL NOT NULL,
                    service_level REAL NOT NULL,
                    risk_level TEXT NOT NULL,
                    risk_label TEXT NOT NULL,
                    risk_reason TEXT NOT NULL,
                    row_index INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS summaries (
                    task_id INTEGER PRIMARY KEY,
                    month TEXT NOT NULL,
                    total_supply REAL NOT NULL,
                    total_sar REAL NOT NULL,
                    total_gap REAL NOT NULL,
                    service_level REAL NOT NULL,
                    target_service_level REAL NOT NULL,
                    inventory_turnover_days REAL NOT NULL,
                    risk_counts TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    operation TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    session_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    references_json TEXT NOT NULL,
                    response_type TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS exports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    export_type TEXT NOT NULL,
                    export_format TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def _seed_users(self) -> None:
        """Insert demo accounts if they are missing."""
        with self.connect() as conn:
            for user in DEMO_USERS.values():
                conn.execute(
                    """
                    INSERT OR IGNORE INTO users
                    (id, username, password, role, real_name)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        user["id"],
                        user["username"],
                        user["password"],
                        user["role"],
                        user["real_name"],
                    ),
                )

    def authenticate(self, username: str, password: str) -> User | None:
        """Return the user when credentials match."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE username = ? AND password = ?",
                (username, password),
            ).fetchone()
        if not row:
            return None
        return User(
            id=int(row["id"]),
            username=str(row["username"]),
            role=str(row["role"]),
            real_name=str(row["real_name"]),
        )

    def create_session(self, user: User, secret_key: str) -> str:
        """Create and persist a bearer token."""
        now = utc_now()
        digest = hashlib.sha256(
            f"{user.username}:{secret_key}:{now}".encode("utf-8")
        ).hexdigest()
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
                (digest, user.id, now),
            )
        self.add_log(user, "LOGIN", "用户登录成功")
        return digest

    def get_user_by_token(self, token: str) -> User | None:
        """Resolve a bearer token to a user."""
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT users.* FROM sessions
                JOIN users ON users.id = sessions.user_id
                WHERE sessions.token = ?
                """,
                (token,),
            ).fetchone()
        if not row:
            return None
        return User(
            id=int(row["id"]),
            username=str(row["username"]),
            role=str(row["role"]),
            real_name=str(row["real_name"]),
        )

    def add_log(self, user: User | None, operation: str, detail: str) -> None:
        """Record an audit log entry."""
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs
                (user_id, username, operation, detail, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user.id if user else None,
                    user.username if user else None,
                    operation,
                    detail,
                    utc_now(),
                ),
            )

    def create_task(
        self, user: User, file_name: str, file_path: Path, file_bytes: bytes
    ) -> int:
        """Create a completed task placeholder for synchronous MVP processing."""
        now = utc_now()
        file_md5 = hashlib.md5(file_bytes, usedforsecurity=False).hexdigest()
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks
                (task_name, file_name, file_path, file_size, file_md5, upload_user_id,
                 status, error_message, progress, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file_name,
                    file_name,
                    str(file_path),
                    len(file_bytes),
                    file_md5,
                    user.id,
                    "PARSING",
                    None,
                    35,
                    now,
                    now,
                ),
            )
            task_id = int(cursor.lastrowid)
        return task_id

    def finish_task(self, task_id: int) -> None:
        """Mark a task as successfully processed."""
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status = 'SUCCESS', progress = 100, error_message = NULL, updated_at = ?
                WHERE id = ?
                """,
                (utc_now(), task_id),
            )

    def fail_task(self, task_id: int, message: str) -> None:
        """Mark a task as failed."""
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status = 'FAILED', progress = 100, error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                (message, utc_now(), task_id),
            )

    def insert_details(self, task_id: int, rows: list[dict[str, Any]]) -> None:
        """Replace task SKU details."""
        with self.connect() as conn:
            conn.execute("DELETE FROM sku_details WHERE task_id = ?", (task_id,))
            conn.executemany(
                """
                INSERT INTO sku_details
                (task_id, month, product_name, sku_code, initial_inventory,
                 production_plan, safety_stock, total_supply, sar_province,
                 sar_dealer, sar_export, sar_internal, sar_total, gap,
                 satisfied_demand, unsatisfied_demand, service_level, risk_level,
                 risk_label, risk_reason, row_index, updated_at)
                VALUES
                (:task_id, :month, :product_name, :sku_code, :initial_inventory,
                 :production_plan, :safety_stock, :total_supply, :sar_province,
                 :sar_dealer, :sar_export, :sar_internal, :sar_total, :gap,
                 :satisfied_demand, :unsatisfied_demand, :service_level, :risk_level,
                 :risk_label, :risk_reason, :row_index, :updated_at)
                """,
                [{**row, "task_id": task_id, "updated_at": utc_now()} for row in rows],
            )

    def upsert_summary(self, task_id: int, summary: dict[str, Any]) -> None:
        """Save aggregate summary for a task."""
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO summaries
                (task_id, month, total_supply, total_sar, total_gap, service_level,
                 target_service_level, inventory_turnover_days, risk_counts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    summary["month"],
                    summary["total_supply"],
                    summary["total_sar"],
                    summary["total_gap"],
                    summary["service_level"],
                    summary["target_service_level"],
                    summary["inventory_turnover_days"],
                    json.dumps(summary["risk_counts"], ensure_ascii=False),
                ),
            )

    def get_task(self, task_id: int) -> dict[str, Any] | None:
        """Fetch a task as a response dictionary."""
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None

    def recent_tasks(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return recent tasks for the workbench."""
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def get_summary(self, task_id: int) -> dict[str, Any] | None:
        """Fetch a task summary."""
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM summaries WHERE task_id = ?", (task_id,)
            ).fetchone()
        if not row:
            return None
        payload = dict(row)
        payload["risk_counts"] = json.loads(payload["risk_counts"])
        return payload

    def get_details(
        self,
        task_id: int,
        risk_level: str | None = None,
        sku_code: str | None = None,
        sort_by: str = "sku_code",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[int, list[dict[str, Any]]]:
        """Fetch paginated SKU details."""
        allowed_sort = {"sku_code", "gap", "service_level", "risk_level"}
        sort_column = sort_by if sort_by in allowed_sort else "sku_code"
        order = "DESC" if sort_order.lower() == "desc" else "ASC"
        filters = ["task_id = ?"]
        params: list[Any] = [task_id]
        if risk_level:
            filters.append("risk_level = ?")
            params.append(risk_level.upper())
        if sku_code:
            filters.append("sku_code LIKE ?")
            params.append(f"%{sku_code}%")
        where_clause = " AND ".join(filters)
        offset = max(page - 1, 0) * page_size
        with self.connect() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM sku_details WHERE {where_clause}", params
            ).fetchone()[0]
            rows = conn.execute(
                f"""
                SELECT * FROM sku_details
                WHERE {where_clause}
                ORDER BY {sort_column} {order}
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()
        return int(total), [dict(row) for row in rows]

    def get_sku(self, task_id: int, sku_code: str) -> dict[str, Any] | None:
        """Fetch one SKU detail."""
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM sku_details
                WHERE task_id = ? AND UPPER(sku_code) = UPPER(?)
                """,
                (task_id, sku_code),
            ).fetchone()
        return dict(row) if row else None

    def save_conversation(
        self,
        user: User,
        task_id: int,
        session_id: str,
        question: str,
        answer: str,
        references: list[dict[str, Any]],
        response_type: str,
    ) -> None:
        """Persist AI conversation history."""
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO conversations
                (task_id, user_id, session_id, question, answer, references_json,
                 response_type, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    user.id,
                    session_id,
                    question,
                    answer,
                    json.dumps(references, ensure_ascii=False),
                    response_type,
                    utc_now(),
                ),
            )

    def create_export(
        self,
        user: User,
        task_id: int,
        export_type: str,
        export_format: str,
        rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Create an export file and database record."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = "csv" if export_format == "csv" else "md"
        file_name = f"产销预测汇总_{task_id}_{timestamp}.{suffix}"
        path = self.export_dir / file_name
        if export_format == "csv":
            with path.open("w", encoding="utf-8-sig", newline="") as file_obj:
                fieldnames = [
                    "month",
                    "product_name",
                    "sku_code",
                    "total_supply",
                    "sar_total",
                    "gap",
                    "service_level",
                    "risk_label",
                    "risk_reason",
                ]
                writer = csv.DictWriter(file_obj, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow({name: row.get(name) for name in fieldnames})
        else:
            with path.open("w", encoding="utf-8") as file_obj:
                file_obj.write(f"# 产销预测逻辑明细 - 任务 {task_id}\n\n")
                for row in rows:
                    file_obj.write(
                        f"- {row['sku_code']} {row['product_name']}: "
                        f"总供应 {row['total_supply']}, 合计SAR {row['sar_total']}, "
                        f"缺口 {row['gap']}, 风险 {row['risk_label']}\n"
                    )
        file_size = path.stat().st_size
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO exports
                (task_id, user_id, export_type, export_format, file_name, file_path,
                 file_size, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    user.id,
                    export_type,
                    export_format,
                    file_name,
                    str(path),
                    file_size,
                    utc_now(),
                ),
            )
            export_id = int(cursor.lastrowid)
        return {
            "export_id": export_id,
            "file_name": file_name,
            "file_size": file_size,
            "status": "SUCCESS",
        }

    def get_export(self, export_id: int) -> dict[str, Any] | None:
        """Fetch export metadata."""
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM exports WHERE id = ?", (export_id,)).fetchone()
        return dict(row) if row else None

    def list_logs(self, page: int = 1, page_size: int = 50) -> tuple[int, list[dict[str, Any]]]:
        """Return audit logs."""
        offset = max(page - 1, 0) * page_size
        with self.connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM audit_logs").fetchone()[0]
            rows = conn.execute(
                """
                SELECT * FROM audit_logs
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                (page_size, offset),
            ).fetchall()
        return int(total), [dict(row) for row in rows]


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()
