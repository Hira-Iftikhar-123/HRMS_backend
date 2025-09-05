from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.project_assignment import ProjectAssignment
from app.schemas.project_assignment import (
    ProjectAssignmentCreate,
    ProjectAssignmentResponse,
)
from app.core.notifications import send_firebase_notification

router = APIRouter(prefix="/projects", tags=["projects"])


def _is_managerial_role(user: User) -> bool:
    return (user.role and user.role.name and user.role.name.lower() in {"admin", "hr", "pm", "manager"})


@router.post("/assign_project", response_model=ProjectAssignmentResponse)
async def assign_project(
    payload: ProjectAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _is_managerial_role(current_user):
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    result = await db.execute(select(User).where(User.id == payload.intern_id))
    intern = result.scalar_one_or_none()
    if not intern:
        raise HTTPException(status_code=404, detail="Intern not found")

    result = await db.execute(select(Project).where(Project.id == payload.project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    assignment = ProjectAssignment(
        intern_id=payload.intern_id,
        project_id=payload.project_id,
        assigned_by_id=current_user.id,
    )
    db.add(assignment)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Intern already assigned to this project")

    await db.refresh(assignment)
    if getattr(intern, "fcm_token", None):
        await send_firebase_notification(
            tokens=intern.fcm_token,
            title="Project Assigned",
            body=f"You have been assigned to project '{project.name}'.",
        )

    return assignment