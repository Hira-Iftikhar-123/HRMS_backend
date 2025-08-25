from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.evaluation import Evaluation
from app.models.project import Project
from app.schemas.evaluation import EvaluationCreate, EvaluationResponse, FinalEvaluationCreate, LockEvaluation, LockStatusResponse, VerdictSubmit, VerdictResponse, VerdictSummaryResponse
from app.models.admin_log import AdminLog
from datetime import datetime


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
                "project_id": payload.project_id
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