"""
任务管理 API
"""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from typing import List
import os
import hashlib
import re
from datetime import datetime
from decimal import Decimal

from app.db import get_db
from app.core.config import get_settings
from app.core.auth import get_optional_user
from app.models.task import TaskFile, TaskSummary
from app.models.sku import SkuForecastDetail
from app.models.ai import AIConversation
from app.models.audit import ExportRecord
from app.models.user import User
from app.schemas.task import TaskResponse, TaskSummaryResponse
from app.schemas.sku import SkuDetailResponse, SkuListResponse
from app.services.forecast_service import ForecastCalculationService
from app.services.parser_service import ExcelParserError
from app.services.audit_service import write_audit_log
from app.services.memory_service import AssistantMemoryService

router = APIRouter()
settings = get_settings()


def _decimal_to_float(value):
    """将 Decimal/None 转换为可 JSON 序列化的数值。"""
    if value is None:
        return 0.0
    return float(value)


def _build_sku_context_rows(db: Session, task_id: int, message: str, limit: int = 20) -> list[dict]:
    """
    构建 AI 对话可用的 SKU 明细上下文。

    优先包含用户问题中点名的 SKU，再补充风险评分高、缺口严重的 SKU。
    """
    sku_codes = {
        match.group(1).replace("_", "-").replace(" ", "-").upper()
        for match in re.finditer(r"(SKU[-_ ]?\d+)", message or "", re.IGNORECASE)
    }
    rows = []
    seen_ids = set()

    if sku_codes:
        exact_rows = (
            db.query(SkuForecastDetail)
            .filter(
                SkuForecastDetail.task_id == task_id,
                SkuForecastDetail.sku_code.in_(sku_codes),
            )
            .all()
        )
        for row in exact_rows:
            rows.append(row)
            seen_ids.add(row.id)

    ranked_rows = (
        db.query(SkuForecastDetail)
        .filter(SkuForecastDetail.task_id == task_id)
        .order_by(SkuForecastDetail.risk_score.desc(), SkuForecastDetail.gap.asc())
        .limit(limit)
        .all()
    )
    for row in ranked_rows:
        if row.id not in seen_ids:
            rows.append(row)
            seen_ids.add(row.id)
        if len(rows) >= limit:
            break

    return [
        {
            "sku_code": row.sku_code,
            "product_name": row.product_name,
            "month": row.month,
            "total_supply": _decimal_to_float(row.total_supply),
            "sar_total": _decimal_to_float(row.sar_total),
            "gap": _decimal_to_float(row.gap),
            "service_level": _decimal_to_float(row.service_level),
            "risk_level": row.risk_level,
            "risk_reason": row.risk_reason,
            "risk_score": _decimal_to_float(row.risk_score),
            "sar_province": _decimal_to_float(row.sar_province),
            "sar_dealer": _decimal_to_float(row.sar_dealer),
            "sar_ecommerce": _decimal_to_float(row.sar_ecommerce),
            "sar_ka": _decimal_to_float(row.sar_ka),
            "sar_expansion": _decimal_to_float(row.sar_expansion),
            "unsatisfied_demand": _decimal_to_float(row.unsatisfied_demand),
        }
        for row in rows
    ]


def _build_conversation_history(db: Session, session_id: str, limit: int = 10) -> list[dict]:
    """
    构建可传给模型的历史对话上下文。

    `AIConversation` 一行保存一轮问答，这里展开成 user/assistant 消息列表。
    """
    rows = (
        db.query(AIConversation)
        .filter(AIConversation.session_id == session_id)
        .order_by(AIConversation.created_at.desc(), AIConversation.id.desc())
        .limit(limit)
        .all()
    )
    history = []
    for row in reversed(rows):
        history.append({"role": "user", "content": row.question})
        history.append({"role": "assistant", "content": row.answer})
    return history


def _conversation_to_message(row: AIConversation) -> dict:
    """将对话记录转换为前端可用的消息结构。"""
    return {
        "id": row.id,
        "session_id": row.session_id,
        "task_id": row.task_id,
        "question": row.question,
        "answer": row.answer,
        "context": row.context,
        "reference": row.reference,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def _next_ai_conversation_id(db: Session) -> int:
    """生成 AI 对话记录 ID，兼容本地 SQLite 旧表的 BigInteger 主键。"""
    max_id = db.query(AIConversation.id).order_by(AIConversation.id.desc()).limit(1).scalar()
    return int(max_id or 0) + 1


@router.post("/tasks/upload", response_model=TaskResponse)
async def upload_file(
    file: UploadFile = File(...),
    task_name: str = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """
    上传并处理预测文件

    Args:
        file: 上传的文件
        task_name: 任务名称
        db: 数据库会话

    Returns:
        任务信息
    """
    # 验证文件类型
    allowed_extensions = {'.xlsx', '.xls', '.csv'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件格式。支持的格式：{', '.join(allowed_extensions)}"
        )

    # 读取文件内容
    file_content = await file.read()
    file_size = len(file_content)

    # 检查文件大小
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制（{settings.max_upload_size_mb}MB）"
        )

    # 计算文件 MD5
    file_md5 = hashlib.md5(file_content).hexdigest()

    # 保存文件
    file_path = settings.upload_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    with open(file_path, 'wb') as f:
        f.write(file_content)

    # 创建任务记录
    task = TaskFile(
        task_name=task_name or file.filename,
        file_name=file.filename,
        file_path=str(file_path),
        file_size=file_size,
        file_md5=file_md5,
        upload_user_id=current_user.id,
        status="PARSING",
        progress=10,
    )
    db.add(task)
    write_audit_log(
        db,
        operation="UPLOAD",
        user=current_user,
        resource_type="TASK",
        resource_id=None,
        detail={"file_name": file.filename, "file_size": file_size, "status": "STARTED"},
        request=request,
    )
    db.commit()
    db.refresh(task)
    task_id = task.id

    # 异步处理文件（这里简化为同步）
    try:
        # 解析和计算
        task.status = "CALCULATING"
        task.progress = 30
        db.commit()

        forecast_service = ForecastCalculationService()
        sku_details, summary = forecast_service.process_forecast_file(str(file_path))

        # 保存 SKU 明细
        task.progress = 60
        db.commit()

        month = datetime.now().strftime('%Y-%m')
        for sku_data in sku_details:
            sku_detail = SkuForecastDetail(
                task_id=task_id,
                month=month,
                product_name=sku_data.get('product_name'),
                sku_code=sku_data.get('sku_code'),
                material_code=sku_data.get('material_code'),
                business_unit=sku_data.get('business_unit'),
                product_series=sku_data.get('product_series'),
                factory=sku_data.get('factory'),
                product_attribute=sku_data.get('product_attribute'),
                product_category=sku_data.get('product_category'),
                ex_factory_price=Decimal(str(sku_data.get('ex_factory_price', 0))),
                launch_date=sku_data.get('launch_date') if sku_data.get('launch_date') else None,
                initial_inventory=Decimal(str(sku_data.get('initial_inventory', 0))),
                production_plan=Decimal(str(sku_data.get('production_plan', 0))),
                safety_stock=Decimal(str(sku_data.get('safety_stock', 0))),
                total_supply=Decimal(str(sku_data.get('total_supply', 0))),
                sar_province=Decimal(str(sku_data.get('sar_province', 0))),
                sar_dealer=Decimal(str(sku_data.get('sar_dealer', 0))),
                sar_ecommerce=Decimal(str(sku_data.get('sar_ecommerce', 0))),
                sar_ka=Decimal(str(sku_data.get('sar_ka', 0))),
                sar_expansion=Decimal(str(sku_data.get('sar_expansion', 0))),
                sar_total=Decimal(str(sku_data.get('sar_total', 0))),
                gap=Decimal(str(sku_data.get('gap', 0))),
                service_level=Decimal(str(sku_data.get('service_level', 0))),
                satisfied_province=Decimal(str(sku_data.get('satisfied_province', 0))),
                satisfied_dealer=Decimal(str(sku_data.get('satisfied_dealer', 0))),
                satisfied_ecommerce=Decimal(str(sku_data.get('satisfied_ecommerce', 0))),
                satisfied_ka=Decimal(str(sku_data.get('satisfied_ka', 0))),
                satisfied_expansion=Decimal(str(sku_data.get('satisfied_expansion', 0))),
                satisfied_demand=Decimal(str(sku_data.get('satisfied_demand', 0))),
                satisfied_ka_before_25=Decimal(str(sku_data.get('satisfied_ka_before_25', 0))),
                unsatisfied_province=Decimal(str(sku_data.get('unsatisfied_province', 0))),
                unsatisfied_dealer=Decimal(str(sku_data.get('unsatisfied_dealer', 0))),
                unsatisfied_ecommerce=Decimal(str(sku_data.get('unsatisfied_ecommerce', 0))),
                unsatisfied_ka=Decimal(str(sku_data.get('unsatisfied_ka', 0))),
                unsatisfied_expansion=Decimal(str(sku_data.get('unsatisfied_expansion', 0))),
                unsatisfied_demand=Decimal(str(sku_data.get('unsatisfied_demand', 0))),
                risk_level=sku_data.get('risk_level'),
                risk_reason=sku_data.get('risk_reason'),
                risk_score=Decimal(str(sku_data.get('risk_score', 0))),
            )
            db.add(sku_detail)

        # 保存汇总数据
        task.progress = 80
        db.commit()

        task_summary = TaskSummary(
            task_id=task_id,
            month=month,
            total_supply=Decimal(str(summary.get('total_supply', 0))),
            total_sar=Decimal(str(summary.get('total_sar', 0))),
            total_gap=Decimal(str(summary.get('total_gap', 0))),
            service_level=Decimal(str(summary.get('service_level', 0))),
            target_service_level=Decimal(str(summary.get('target_service_level', 98))),
            critical_risk_count=summary.get('critical_risk_count', 0),
            high_risk_count=summary.get('high_risk_count', 0),
            medium_risk_count=summary.get('medium_risk_count', 0),
        )
        db.add(task_summary)

        # 完成
        task.status = "SUCCESS"
        task.progress = 100
        write_audit_log(
            db,
            operation="TASK_SUCCESS",
            user=current_user,
            resource_type="TASK",
            resource_id=task_id,
            detail={"file_name": task.file_name, "sku_count": len(sku_details)},
            request=request,
        )
        db.commit()

    except ExcelParserError as e:
        db.rollback()
        failed_task = db.query(TaskFile).filter(TaskFile.id == task_id).first()
        if failed_task:
            failed_task.status = "FAILED"
            failed_task.error_message = str(e)
        write_audit_log(
            db,
            operation="TASK_FAILED",
            user=current_user,
            resource_type="TASK",
            resource_id=task_id,
            detail={"file_name": file.filename, "error": str(e)},
            request=request,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件解析失败: {str(e)}"
        )
    except Exception as e:
        db.rollback()
        failed_task = db.query(TaskFile).filter(TaskFile.id == task_id).first()
        if failed_task:
            failed_task.status = "FAILED"
            failed_task.error_message = str(e)
        write_audit_log(
            db,
            operation="TASK_FAILED",
            user=current_user,
            resource_type="TASK",
            resource_id=task_id,
            detail={"file_name": file.filename, "error": str(e)},
            request=request,
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"处理失败: {str(e)}"
        )

    db.refresh(task)
    return task


@router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    获取任务列表

    Args:
        skip: 跳过数量
        limit: 返回数量
        db: 数据库会话

    Returns:
        任务列表
    """
    tasks = db.query(TaskFile).order_by(TaskFile.created_at.desc()).offset(skip).limit(limit).all()
    return tasks


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: Session = Depends(get_db)):
    """
    获取任务详情

    Args:
        task_id: 任务ID
        db: 数据库会话

    Returns:
        任务详情
    """
    task = db.query(TaskFile).filter(TaskFile.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )
    return task


@router.get("/tasks/{task_id}/summary", response_model=TaskSummaryResponse)
async def get_task_summary(task_id: int, db: Session = Depends(get_db)):
    """
    获取任务汇总

    Args:
        task_id: 任务ID
        db: 数据库会话

    Returns:
        汇总数据
    """
    summary = db.query(TaskSummary).filter(TaskSummary.task_id == task_id).first()
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="汇总数据不存在"
        )
    return summary


@router.get("/tasks/{task_id}/sku-details", response_model=SkuListResponse)
async def get_sku_details(
    task_id: int,
    page: int = 1,
    page_size: int = 50,
    risk_level: str = None,
    db: Session = Depends(get_db)
):
    """
    获取 SKU 明细列表

    Args:
        task_id: 任务ID
        page: 页码
        page_size: 每页大小
        risk_level: 风险等级过滤
        db: 数据库会话

    Returns:
        SKU 列表
    """
    query = db.query(SkuForecastDetail).filter(SkuForecastDetail.task_id == task_id)

    if risk_level:
        query = query.filter(SkuForecastDetail.risk_level == risk_level)

    # 按风险评分降序排序
    query = query.order_by(SkuForecastDetail.risk_score.desc())

    # 分页
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return SkuListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items
    )


@router.get("/tasks/{task_id}/sku-details/{sku_id}", response_model=SkuDetailResponse)
async def get_sku_detail(
    task_id: int,
    sku_id: int,
    db: Session = Depends(get_db)
):
    """
    获取 SKU 明细

    Args:
        task_id: 任务ID
        sku_id: SKU ID
        db: 数据库会话

    Returns:
        SKU 明细
    """
    sku_detail = db.query(SkuForecastDetail).filter(
        SkuForecastDetail.task_id == task_id,
        SkuForecastDetail.id == sku_id
    ).first()

    if not sku_detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="SKU明细不存在"
        )

    return sku_detail


@router.post("/tasks/{task_id}/export")
async def export_task_data(
    task_id: int,
    export_type: str = "SKU_DETAIL",
    export_format: str = "XLSX",
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """
    导出任务数据

    Args:
        task_id: 任务ID
        export_type: 导出类型（SUMMARY, SKU_DETAIL）
        export_format: 导出格式（XLSX, CSV）
        db: 数据库会话

    Returns:
        文件下载响应
    """
    from fastapi.responses import FileResponse
    from app.services.export_service import ExportService
    
    # 验证任务存在
    task = db.query(TaskFile).filter(TaskFile.id == task_id).first()
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任务不存在"
        )

    # 创建导出服务
    export_service = ExportService()
    
    # 生成文件名
    filename = export_service.generate_export_filename(export_type, export_format, task_id)
    output_path = settings.upload_dir / "exports" / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if export_type in {"SUMMARY", "SKU_DETAIL"}:
            # 导出SKU明细
            sku_details = db.query(SkuForecastDetail).filter(
                SkuForecastDetail.task_id == task_id
            ).order_by(SkuForecastDetail.risk_score.desc()).all()

            if not sku_details:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="SKU明细不存在"
                )

            # 转换为字典列表
            data = []
            for sku in sku_details:
                data.append({
                    '事业部': sku.business_unit,
                    '产品系列': sku.product_series,
                    '生产工厂': sku.factory,
                    '属性': sku.product_attribute,
                    '型号': sku.sku_code,
                    '产品描述': sku.product_name,
                    '产品类别': sku.product_category,
                    '出厂价': float(sku.ex_factory_price or 0),
                    '上市日期': sku.launch_date.strftime("%Y-%m-%d") if sku.launch_date else None,
                    '4.30日库存': float(sku.initial_inventory or 0),
                    '5月排产（4.30-5.29）': float(sku.production_plan or 0),
                    '5月总供应': float(sku.total_supply or 0),
                    '省大区SAR': float(sku.sar_province or 0),
                    '网络经销商SAR': float(sku.sar_dealer or 0),
                    '电商直营SAR': float(sku.sar_ecommerce or 0),
                    'KA部SAR': float(sku.sar_ka or 0),
                    '拓展部SAR': float(sku.sar_expansion or 0),
                    '5月SAR合计': float(sku.sar_total or 0),
                    '5月SAR差异': float(sku.gap or 0),
                    '可满足合计': float(sku.satisfied_demand or 0),
                    '省大区（可满足）': float(sku.satisfied_province or 0),
                    '网络经销商（可满足）': float(sku.satisfied_dealer or 0),
                    '电商直营（可满足）': float(sku.satisfied_ecommerce or 0),
                    'KA部（可满足）': float(sku.satisfied_ka or 0),
                    '拓展部（可满足）': float(sku.satisfied_expansion or 0),
                    'KA-5月25日前可满足（含25日）': float(sku.satisfied_ka_before_25 or 0),
                    '未满足合计': float(sku.unsatisfied_demand or 0),
                    '省大区（未满足）': float(sku.unsatisfied_province or 0),
                    '网络经销商（未满足）': float(sku.unsatisfied_dealer or 0),
                    '电商直营（未满足）': float(sku.unsatisfied_ecommerce or 0),
                    'KA部（未满足）': float(sku.unsatisfied_ka or 0),
                    '拓展部（未满足）': float(sku.unsatisfied_expansion or 0),
                    'SKU编码': sku.sku_code,
                    '产品名称': sku.product_name,
                    '总供应': float(sku.total_supply or 0),
                    '省大区SAR': float(sku.sar_province or 0),
                    '网络经销商SAR': float(sku.sar_dealer or 0),
                    '电商直营SAR': float(sku.sar_ecommerce or 0),
                    'KA部SAR': float(sku.sar_ka or 0),
                    '拓展部SAR': float(sku.sar_expansion or 0),
                    '合计SAR': float(sku.sar_total or 0),
                    '缺口': float(sku.gap or 0),
                    '满足率': float(sku.service_level or 0),
                    '可满足合计': float(sku.satisfied_demand or 0),
                    '未满足合计': float(sku.unsatisfied_demand or 0),
                    '风险等级': sku.risk_level,
                    '风险评分': float(sku.risk_score or 0),
                    '风险原因': sku.risk_reason,
                })

            if export_format == "XLSX":
                export_service.export_summary_template(data, str(output_path))
            else:
                export_service.export_to_csv(data, str(output_path))
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不支持的导出类型",
            )

        # 记录导出
        export_record = ExportRecord(
            task_id=task_id,
            user_id=current_user.id,
            export_type=export_type,
            export_format=export_format,
            file_name=filename,
            file_path=str(output_path),
            file_size=output_path.stat().st_size if output_path.exists() else 0,
        )
        db.add(export_record)
        write_audit_log(
            db,
            operation="EXPORT",
            user=current_user,
            resource_type="TASK",
            resource_id=task_id,
            detail={
                "export_type": export_type,
                "export_format": export_format,
                "file_name": filename,
                "file_size": export_record.file_size,
            },
            request=request,
        )
        db.commit()

        # 返回文件
        return FileResponse(
            path=str(output_path),
            filename=filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' if export_format == 'XLSX' else 'text/csv'
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"导出失败: {str(e)}"
        )


@router.get("/chat/sessions")
async def list_chat_sessions(
    task_id: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    查询 AI 对话会话列表。

    Returns:
        每个会话的最近一轮对话、标题和消息数量。
    """
    query = db.query(AIConversation)
    if task_id:
        query = query.filter(AIConversation.task_id == task_id)

    rows = query.order_by(AIConversation.created_at.desc(), AIConversation.id.desc()).all()
    sessions = {}
    for row in rows:
        if row.session_id not in sessions:
            sessions[row.session_id] = {
                "session_id": row.session_id,
                "task_id": row.task_id,
                "title": row.question[:60],
                "last_question": row.question,
                "last_answer": row.answer,
                "message_count": 0,
                "updated_at": row.created_at.isoformat() if row.created_at else None,
            }
        sessions[row.session_id]["message_count"] += 1
        if not sessions[row.session_id].get("created_at"):
            sessions[row.session_id]["created_at"] = row.created_at.isoformat() if row.created_at else None

    return list(sessions.values())[:limit]


@router.get("/chat/sessions/{session_id}")
async def get_chat_session(
    session_id: str,
    db: Session = Depends(get_db),
):
    """
    查询某个 AI 会话的完整历史。
    """
    rows = (
        db.query(AIConversation)
        .filter(AIConversation.session_id == session_id)
        .order_by(AIConversation.created_at.asc(), AIConversation.id.asc())
        .all()
    )
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="会话不存在"
        )

    return {
        "session_id": session_id,
        "task_id": rows[-1].task_id,
        "title": rows[0].question[:60],
        "message_count": len(rows),
        "messages": [_conversation_to_message(row) for row in rows],
    }


@router.post("/chat")
async def chat_with_ai(
    request: dict,
    fastapi_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    """
    AI对话接口

    Args:
        request: 包含session_id, message, task_id等
        db: 数据库会话

    Returns:
        AI回复
    """
    from app.services.ai_service import AIService
    
    session_id = request.get("session_id", "default")
    message = request.get("message", "")
    task_id = request.get("task_id")
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="消息不能为空"
        )
    
    # 构建上下文
    context = {}
    if task_id:
        # 获取任务汇总数据
        summary = db.query(TaskSummary).filter(TaskSummary.task_id == task_id).first()
        if summary:
            context["task_summary"] = {
                "total_supply": float(summary.total_supply or 0),
                "total_sar": float(summary.total_sar or 0),
                "total_gap": float(summary.total_gap or 0),
                "service_level": float(summary.service_level or 0),
                "target_service_level": float(summary.target_service_level or 98),
                "critical_risk_count": summary.critical_risk_count,
                "high_risk_count": summary.high_risk_count,
                "medium_risk_count": summary.medium_risk_count,
            }
        context["sku_details"] = _build_sku_context_rows(db, task_id, message)
    context["conversation_history"] = _build_conversation_history(db, session_id)
    memory_service = AssistantMemoryService()
    long_term_memories = memory_service.search(
        message,
        user_id=current_user.id,
        limit=settings.memory_search_limit,
    )
    if long_term_memories:
        context["long_term_memories"] = long_term_memories
        context["long_term_memory_text"] = memory_service.format_for_prompt(long_term_memories)
    
    # 调用AI服务
    ai_service = AIService()
    response = ai_service.chat(session_id, message, context)

    conversation = AIConversation(
        id=_next_ai_conversation_id(db),
        task_id=task_id,
        user_id=current_user.id,
        session_id=session_id,
        question=message,
        answer=response.get("message", ""),
        context=context,
        reference={
            "task_id": task_id,
            "sku_count": len(context.get("sku_details", [])),
            "history_message_count": len(context.get("conversation_history", [])),
        },
    )
    db.add(conversation)
    write_audit_log(
        db,
        operation="AI_CHAT",
        user=current_user,
        resource_type="TASK" if task_id else "CHAT",
        resource_id=task_id,
        detail={"session_id": session_id, "conversation_id": None, "success": response.get("success")},
        request=fastapi_request,
    )
    db.commit()
    db.refresh(conversation)
    memory_service.add_interaction(
        user_message=message,
        assistant_message=response.get("message", ""),
        user_id=current_user.id,
        session_id=session_id,
        metadata={"task_id": task_id, "conversation_id": conversation.id},
    )
    response["conversation_id"] = conversation.id

    return response
