from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from app.core.database import get_db
from app.models.project import Project
from app.models.task import Task
from app.models.leave import Leave
from app.core.auth import get_current_user
from app.models.user import User
from typing import Dict, Any

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/ceo-metrics")
async def get_ceo_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role_id != 6:
        raise HTTPException(status_code=403, detail="Access denied. CEO role required.")
    
    result = await db.execute(select(func.count(Project.id)))
    total_projects = result.scalar()
    
    result = await db.execute(select(func.count(Task.id)))
    total_tasks = result.scalar()
    
    result = await db.execute(select(func.count(Leave.id)).where(Leave.status == "pending"))
    pending_leaves = result.scalar()
    
    return {
        "total_projects": total_projects,
        "total_tasks": total_tasks,
        "pending_leaves": pending_leaves
    }

@router.get("/task-status-summary")
async def get_task_status_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role_id != 6:
        raise HTTPException(status_code=403, detail="Access denied. CEO role required.")
    
    result = await db.execute(
        select(Task.status, func.count(Task.id).label('count'))
        .group_by(Task.status)
    )
    task_status_counts = result.all()
    
    status_summary = {}
    for status, count in task_status_counts:
        status_summary[status] = count
    
    return {
        "task_status_summary": status_summary
    } 