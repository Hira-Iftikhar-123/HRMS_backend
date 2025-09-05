from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.evaluation import Evaluation
from app.models.project import Project
from app.schemas.evaluation import EvaluationCreate, EvaluationResponse, FinalEvaluationCreate, LockEvaluation, LockStatusResponse, VerdictSubmit, VerdictResponse, VerdictSummaryResponse, EvaluationArchiveResponse, EvaluationHistoryResponse, EvaluationHistoryItem, SignatureRejectionRequest, SignatureRejectionResponse, InternReportData
from app.models.admin_log import AdminLog
from app.models.attendance import Attendance
from app.models.leave import Leave
from app.models.task import Task
from app.models.feedback import Feedback
from app.core.notifications import send_firebase_notification, verify_and_store_signature
from app.core.security import rate_limit_sensitive
from datetime import datetime
from sqlalchemy.orm import aliased
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from fastapi.responses import StreamingResponse
from fastapi import Request
from sqlalchemy import cast, String

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


def _is_pm_or_manager(user: User) -> bool:
    return user.role and user.role.name and user.role.name.lower() in {"pm", "manager", "admin"}


@router.post("/evaluate", response_model=EvaluationResponse)
async def submit_evaluation(
    payload: EvaluationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _is_pm_or_manager(current_user):
        raise HTTPException(status_code=403, detail="Only PM/Manager/Admin can evaluate")

    result = await db.execute(select(User).where(User.id == payload.intern_id))
    intern = result.scalar_one_or_none()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")

    result = await db.execute(select(Project).where(Project.id == payload.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    evaluation = Evaluation(
        evaluator_id=current_user.id,
        intern_id=payload.intern_id,
        project_id=payload.project_id,
        stars=payload.stars,
        comment=payload.comment,
    )
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)
    return evaluation


@router.get("/evaluations/{intern_id}", response_model=List[EvaluationResponse])
async def get_evaluations(
    intern_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Evaluation).where(Evaluation.intern_id == intern_id)
        .order_by(Evaluation.created_at.desc())
    )
    return result.scalars().all()

@router.post("/final", response_model=EvaluationResponse)
async def submit_final_evaluation(
    payload: FinalEvaluationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _is_pm_or_manager(current_user):
        raise HTTPException(status_code=403, detail="Only PM/Manager/Admin can submit final evaluation")

    result = await db.execute(select(User).where(User.id == payload.intern_id))
    intern = result.scalar_one_or_none()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")

    result = await db.execute(select(Project).where(Project.id == payload.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    signature_verification_result = None
    if payload.signature:
        signature_verification_result = await verify_and_store_signature(
            db=db,
            user_id=payload.intern_id,
            signature_data=payload.signature,
            evaluator_id=None  
        )
        signature_verified = signature_verification_result["is_valid"]
    else:
        signature_verified = False

    evaluation = Evaluation(
        evaluator_id=current_user.id,
        intern_id=payload.intern_id,
        project_id=payload.project_id,
        comment=payload.evaluator_remark,
        is_final=True,
        criteria=payload.criteria,
        signature=payload.signature,
        stars=payload.stars,
    )
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)

    try:
        db.add(AdminLog(
            type="evaluation_final",
            message="Final evaluation submitted",
            actor_user_id=current_user.id,
            meta={
                "intern_id": payload.intern_id,
                "project_id": payload.project_id,
                "signature_verified": signature_verified,
                "signature_hash": signature_verification_result["signature_hash"] if signature_verification_result else None
            }
        ))
        await db.commit()
    except Exception:
        pass

    return evaluation

@router.post('/lock_evaluation', response_model=LockStatusResponse)
async def lock_evaluation(
    data: LockEvaluation,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _is_pm_or_manager(current_user):
        raise HTTPException(status_code=403, detail="Only PM/Manager/Admin can lock evaluations")
 
    result = await db.execute(select(User).where(User.id == data.intern_id))
    intern = result.scalar_one_or_none()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")
    
    result = await db.execute(
        select(Evaluation).where(Evaluation.intern_id == data.intern_id)
    )
    evaluations = result.scalars().all()
    
    if not evaluations:
        raise HTTPException(status_code=404, detail="No evaluations found for this intern")
    
    for evaluation in evaluations:
        evaluation.lock_status = data.lock_status
    
    await db.commit()
    
    try:
        db.add(AdminLog(
            type="evaluation_lock",
            message=f"Evaluation lock status updated to {data.lock_status}",
            actor_user_id=current_user.id,
            meta={
                "intern_id": data.intern_id,
                "lock_status": data.lock_status
            }
        ))
        await db.commit()
    except Exception:
        pass
    
    return LockStatusResponse(intern_id=data.intern_id, lock_status=data.lock_status)

@router.get('/lock_status/{intern_id}', response_model=LockStatusResponse)
async def get_lock_status(
    intern_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == intern_id))
    intern = result.scalar_one_or_none()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")
    
    result = await db.execute(
        select(Evaluation).where(Evaluation.intern_id == intern_id)
        .order_by(Evaluation.created_at.desc())
    )
    evaluation = result.scalar_one_or_none()
    
    if not evaluation:
        return LockStatusResponse(intern_id=intern_id, lock_status=False)
    
    return LockStatusResponse(intern_id=intern_id, lock_status=evaluation.lock_status)

@router.post('/submit_verdict', response_model=VerdictResponse)
async def submit_verdict(
    payload: VerdictSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _is_pm_or_manager(current_user):
        raise HTTPException(status_code=403, detail="Only PM/Manager/Admin can submit verdict")

    result = await db.execute(select(User).where(User.id == payload.intern_id))
    intern = result.scalar_one_or_none()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")

    result = await db.execute(
        select(Evaluation).where(
            Evaluation.intern_id == payload.intern_id,
            Evaluation.lock_status == True
        ).order_by(Evaluation.created_at.desc())
    )
    locked_eval = result.scalar_one_or_none()

    if not locked_eval:
        raise HTTPException(status_code=400, detail="Evaluations must be locked before submitting a verdict")

    submitted_at = datetime.utcnow()

    try:
        db.add(AdminLog(
            type="evaluation_verdict",
            message="Verdict submitted",
            actor_user_id=current_user.id,
            meta={
                "intern_id": payload.intern_id,
                "verdict": payload.verdict,
                "remarks": payload.remarks,
                "submitted_at": submitted_at.isoformat() + 'Z'
            }
        ))
        await db.commit()
    except Exception:
        pass

    return VerdictResponse(
        intern_id=payload.intern_id,
        verdict=payload.verdict,
        remarks=payload.remarks,
        submitted_by=current_user.id,
        submitted_at=submitted_at,
    )

@router.get('/verdict_summary/{intern_id}', response_model=VerdictSummaryResponse)
async def verdict_summary(
    intern_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(User).where(User.id == intern_id))
    intern = result.scalar_one_or_none()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")

    result = await db.execute(
        select(Evaluation).where(Evaluation.intern_id == intern_id)
        .order_by(Evaluation.created_at.desc())
    )
    evaluations = result.scalars().all()

    if not evaluations:
        return VerdictSummaryResponse(
            intern_id=intern_id,
            total_evaluations=0,
            average_stars=None,
            is_locked=False,
            last_comment=None,
            last_evaluated_at=None,
        )

    total = len(evaluations)
    stars = [e.stars for e in evaluations if e.stars is not None]
    avg = round(sum(stars) / len(stars), 2) if stars else None
    is_locked = any(e.lock_status for e in evaluations)
    last_comment = evaluations[0].comment
    last_evaluated_at = evaluations[0].created_at

    return VerdictSummaryResponse(
        intern_id=intern_id,
        total_evaluations=total,
        average_stars=avg,
        is_locked=is_locked,
        last_comment=last_comment,
        last_evaluated_at=last_evaluated_at,
    )

@router.get('/evaluation_archive', response_model=List[EvaluationArchiveResponse])
async def evaluation_archive(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    intern_id: Optional[int] = None,
    date_range: Optional[str] = None,
    verdict: Optional[str] = None,
):
    # Check if user has HR or Admin role
    if not current_user.role or current_user.role.name.lower() not in {"hr", "admin"}:
        raise HTTPException(status_code=403, detail="Only HR and Admin can access evaluation archive")
    
    InternUser = aliased(User)
    EvaluatorUser = aliased(User)
    
    query = select(
        Evaluation,
        InternUser.full_name.label("intern_name"),
        EvaluatorUser.full_name.label("evaluator_name"),
        Project.name.label("project_name")
    ).select_from(Evaluation
    ).join(InternUser, Evaluation.intern_id == InternUser.id, isouter=True
    ).join(EvaluatorUser, Evaluation.evaluator_id == EvaluatorUser.id, isouter=True
    ).join(Project, Evaluation.project_id == Project.id, isouter=True)
    
    # Apply filters
    if intern_id:
        query = query.where(Evaluation.intern_id == intern_id)
    
    if date_range:
        try:
            start_date, end_date = date_range.split(",")
            start_dt = datetime.strptime(start_date.strip(), "%Y-%m-%d")
            end_dt = datetime.strptime(end_date.strip(), "%Y-%m-%d")
            query = query.where(Evaluation.created_at >= start_dt, Evaluation.created_at <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date range format. Use YYYY-MM-DD,YYYY-MM-DD")
    
    if verdict:
        verdict_query = select(cast(AdminLog.meta["intern_id"], String)).where(
            AdminLog.type == "evaluation_verdict",
            cast(AdminLog.meta["verdict"], String) == verdict
        )
        query = query.where(cast(Evaluation.intern_id, String).in_(verdict_query))
    
    query = query.order_by(Evaluation.created_at.desc())
    
    result = await db.execute(query)
    evaluations = result.all()
    
    response_data = []
    for eval_data in evaluations:
        evaluation, intern_name, evaluator_name, project_name = eval_data
        response_data.append(EvaluationArchiveResponse(
            id=evaluation.id,
            evaluator_id=evaluation.evaluator_id,
            intern_id=evaluation.intern_id,
            project_id=evaluation.project_id,
            stars=evaluation.stars,
            comment=evaluation.comment,
            is_final=evaluation.is_final,
            criteria=evaluation.criteria,
            signature=evaluation.signature,
            lock_status=evaluation.lock_status,
            created_at=evaluation.created_at,
            intern_name=intern_name,
            evaluator_name=evaluator_name,
            project_name=project_name
        ))
    
    return response_data


@router.get('/evaluation_history/{intern_id}', response_model=EvaluationHistoryResponse)
async def evaluation_history(
    intern_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.role or current_user.role.name.lower() not in {"hr", "admin"}:
        raise HTTPException(status_code=403, detail="Only HR and Admin can access evaluation history")
    
    result = await db.execute(select(User).where(User.id == intern_id))
    intern = result.scalar_one_or_none()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")
    
    ActorUser = aliased(User)
    result = await db.execute(
        select(AdminLog, ActorUser.full_name.label("actor_name")).join(
            ActorUser, AdminLog.actor_user_id == ActorUser.id, isouter=True
        ).where(
            AdminLog.type.in_(["evaluation_lock", "evaluation_verdict", "evaluation_final"]),
            cast(AdminLog.meta["intern_id"], String) == str(intern_id)
        ).order_by(AdminLog.created_at.desc())
    )
    
    logs = result.all()
    
    history_items = []
    for log_data in logs:
        log, actor_name = log_data
        history_items.append(EvaluationHistoryItem(
            id=log.id,
            type=log.type,
            message=log.message,
            actor_user_id=log.actor_user_id,
            actor_name=actor_name,
            meta=log.meta,
            created_at=log.created_at
        ))
    
    return EvaluationHistoryResponse(
        intern_id=intern_id,
        intern_name=intern.full_name,
        history=history_items
    )


@router.post('/reject_signature', response_model=SignatureRejectionResponse)
@rate_limit_sensitive()
async def reject_signature(
    request: Request,
    payload: SignatureRejectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Role-based access control - only Admin can reject signatures
    if not current_user.role or current_user.role.name.lower() != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can reject digital signatures")
    
    # Verify intern exists
    result = await db.execute(select(User).where(User.id == payload.intern_id))
    intern = result.scalar_one_or_none()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")
    
    # Verify evaluation exists and has a signature
    result = await db.execute(select(Evaluation).where(Evaluation.id == payload.evaluation_id))
    evaluation = result.scalar_one_or_none()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    if evaluation.intern_id != payload.intern_id:
        raise HTTPException(status_code=400, detail="Evaluation does not belong to the specified intern")
    
    if not evaluation.signature:
        raise HTTPException(status_code=400, detail="Evaluation does not have a signature to reject")
    
    # Clear the signature
    evaluation.signature = None
    await db.commit()
    
    # Log the action
    try:
        db.add(AdminLog(
            type="signature_rejection",
            message=f"Digital signature rejected: {payload.reason}",
            actor_user_id=current_user.id,
            meta={
                "intern_id": payload.intern_id,
                "evaluation_id": payload.evaluation_id,
                "reason": payload.reason
            }
        ))
        await db.commit()
    except Exception:
        pass
    
    # Send push notification to Flutter app
    if intern.fcm_token:
        try:
            await send_firebase_notification(
                tokens=intern.fcm_token,
                title="Digital Signature Rejected",
                body=f"Your digital signature has been rejected. Reason: {payload.reason}",
            )
        except Exception:
            pass  # Don't fail the request if notification fails
    
    return SignatureRejectionResponse(
        success=True,
        message="Digital signature rejected successfully",
        evaluation_id=payload.evaluation_id,
        intern_id=payload.intern_id
    )


@router.get('/generate_report/{intern_id}')
async def generate_intern_report(
    intern_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.role or current_user.role.name.lower() not in {"hr", "admin", "pm", "manager"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions to generate intern report")
    
    result = await db.execute(select(User).where(User.id == intern_id))
    intern = result.scalar_one_or_none()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")
    
    result = await db.execute(select(Attendance).where(Attendance.user_id == intern_id))
    attendance_records = result.scalars().all()
    
    total_days = len(attendance_records)
    present_days = sum(1 for record in attendance_records if record.present)
    attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
    
    result = await db.execute(select(Leave).where(Leave.user_id == intern_id))
    leave_count = len(result.scalars().all())
    
    result = await db.execute(select(Task).where(Task.assigned_to_id == intern_id))
    tasks = result.scalars().all()
    total_tasks = len(tasks)
    tasks_completed = sum(1 for task in tasks if task.status == "approved")
    
    result = await db.execute(select(Feedback).where(Feedback.intern_id == intern_id))
    feedbacks = result.scalars().all()
    average_rating = 0
    if feedbacks:
        total_rating = sum(feedback.rating for feedback in feedbacks)
        average_rating = total_rating / len(feedbacks)
    
    result = await db.execute(
        select(AdminLog).where(
            AdminLog.type == "evaluation_verdict",
            cast(AdminLog.meta["intern_id"], String) == str(intern_id)
        ).order_by(AdminLog.created_at.desc())
    )
    latest_verdict_row = result.first()
    latest_verdict = latest_verdict_row[0] if latest_verdict_row else None
    verdict = latest_verdict.meta.get("verdict") if latest_verdict else None
    remarks = latest_verdict.meta.get("remarks") if latest_verdict else None
    
    # Generate PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  
    )
    story.append(Paragraph(f"Intern Performance Report", title_style))
    story.append(Spacer(1, 20))
    
    # Intern Information
    story.append(Paragraph(f"<b>Intern Information:</b>", styles['Heading2']))
    story.append(Paragraph(f"Name: {intern.full_name}", styles['Normal']))
    story.append(Paragraph(f"Email: {intern.email}", styles['Normal']))
    story.append(Paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Performance Metrics
    story.append(Paragraph(f"<b>Performance Metrics:</b>", styles['Heading2']))
    
    # Create table for metrics
    data = [
        ['Metric', 'Value'],
        ['Attendance Percentage', f'{attendance_percentage:.1f}%'],
        ['Leave Count', str(leave_count)],
        ['Tasks Completed', f'{tasks_completed}/{total_tasks}'],
        ['Average Rating', f'{average_rating:.2f}/5.0'],
    ]
    
    if verdict:
        data.append(['Verdict', verdict])
    if remarks:
        data.append(['Remarks', remarks])
    
    table = Table(data, colWidths=[2*inch, 3*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(table)
    story.append(Spacer(1, 20))
    
    doc.build(story)
    buffer.seek(0)
    
    try:
        db.add(AdminLog(
            type="intern_report",
            message="Intern performance report generated",
            actor_user_id=current_user.id,
            meta={
                "intern_id": intern_id,
                "intern_name": intern.full_name,
                "attendance_percentage": attendance_percentage,
                "leave_count": leave_count,
                "tasks_completed": tasks_completed,
                "total_tasks": total_tasks,
                "average_rating": average_rating
            }
        ))
        await db.commit()
    except Exception:
        pass
    
    return StreamingResponse(
        io.BytesIO(buffer.getvalue()),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=intern_report_{intern_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        }
    )


@router.post('/verify_signature')
async def verify_signature(
    signature_data: str,
    evaluation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.role or current_user.role.name.lower() not in {"hr", "admin", "pm", "manager"}:
        raise HTTPException(status_code=403, detail="Insufficient permissions to verify signatures")
    
    result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
    evaluation = result.scalar_one_or_none()
    if not evaluation:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    
    result = await db.execute(
        select(AdminLog).where(
            AdminLog.type == "evaluation_final",
            cast(AdminLog.meta["project_id"], String) == str(evaluation.project_id),
            cast(AdminLog.meta["intern_id"], String) == str(evaluation.intern_id)
        ).order_by(AdminLog.created_at.desc())
    )
    latest_log = result.scalar_one_or_none()
    expected_hash = latest_log.meta.get("signature_hash") if latest_log else None
    
    # Verify signature
    verification_result = await verify_and_store_signature(
        db=db,
        user_id=evaluation.intern_id,
        signature_data=signature_data,
        evaluation_id=evaluation_id,
        expected_hash=expected_hash
    )
    
    return {
        "evaluation_id": evaluation_id,
        "intern_id": evaluation.intern_id,
        "signature_verified": verification_result["is_valid"],
        "signature_hash": verification_result["signature_hash"],
        "expected_hash": expected_hash,
        "verified_at": verification_result["verified_at"]
    }