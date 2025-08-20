from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.evaluation import Evaluation
from app.models.project import Project
from app.schemas.evaluation import EvaluationCreate, EvaluationResponse, FinalEvaluationCreate
from app.models.admin_log import AdminLog


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

    # Validate intern
    result = await db.execute(select(User).where(User.id == payload.intern_id))
    intern = result.scalar_one_or_none()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")

    # Validate project
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
    # Any authenticated user can view; you may restrict later
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

    # Validate intern
    result = await db.execute(select(User).where(User.id == payload.intern_id))
    intern = result.scalar_one_or_none()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")

    # Validate project
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

    # Log the action
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
        # Non-blocking log failure
        pass

    return evaluation