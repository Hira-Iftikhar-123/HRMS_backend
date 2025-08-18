from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from pydantic import BaseModel
from app.core.database import get_db
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.core.auth import get_current_user, require_roles
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/task", tags=["Task"])

class TaskProgressUpdate(BaseModel):
    progress: int  # Progress percentage (0-100)

@router.get("/debug-user")
async def debug_user_info(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Debug endpoint to check user role information"""
    return {
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role_id": user.role_id,
        "role_name": user.role.name if user.role else "No role",
        "role_object": {
            "id": user.role.id,
            "name": user.role.name
        } if user.role else None
    }

@router.post("/assign-task", response_model=TaskResponse)
async def assign_task(task_in: TaskCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Assign task - check role manually for debugging"""
    if not user.role or user.role.name not in ["Admin", "Manager"]:
        raise HTTPException(
            status_code=403, 
            detail=f"Insufficient permissions. User role: {user.role.name if user.role else 'None'}, Required: Admin or Manager"
        )
    
    task = Task(**task_in.dict())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task

@router.get("/my-tasks/{user_id}", response_model=List[TaskResponse])
async def get_my_tasks(user_id: int, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    if user.id != user_id and user.role.name not in ["Admin", "Manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    result = await db.execute(select(Task).filter(Task.assigned_to_id == user_id))
    return result.scalars().all()

@router.patch("/task-status/{task_id}", response_model=TaskResponse)
async def update_task_status(task_id: int, update: TaskUpdate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    result = await db.execute(select(Task).filter(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if user.id != task.assigned_to_id and user.role.name not in ["Admin", "Manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    task.status = update.status
    await db.commit()
    await db.refresh(task)
    logger.info(f"Task ID {task.id} status updated to '{task.status}' by {user.username}")
    return task

@router.patch("/task-progress/{task_id}", response_model=TaskResponse)
async def update_task_progress(task_id: int, progress_update: TaskProgressUpdate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    """Update task progress percentage (0-100)"""
    # Validate progress value
    if not 0 <= progress_update.progress <= 100:
        raise HTTPException(status_code=400, detail="Progress must be between 0 and 100")
    
    result = await db.execute(select(Task).filter(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Only assigned user or admin/manager can update progress
    if user.id != task.assigned_to_id and user.role.name not in ["Admin", "Manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to update this task's progress")
    
    task.progress = progress_update.progress
    await db.commit()
    await db.refresh(task)
    logger.info(f"Task ID {task.id} progress updated to {task.progress}% by user ID {user.id}")
    return task 

@router.patch("/update_task_status", response_model=TaskResponse)
async def update_task_status(intern_id: int, task_id: int, status: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):

    valid_statuses = ["pending", "approved", "rejected"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    # Check if user has permission (Admin, Manager, or the assigned intern) 
    if user.role.name not in ["Admin", "Manager"] and user.id != intern_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this task status")
    
    result = await db.execute(select(Task).filter(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.assigned_to_id != intern_id:
        raise HTTPException(status_code=400, detail="Task is not assigned to the specified intern")
    
    # Validate task belongs to a project
    if not task.project_id:
        raise HTTPException(status_code=400, detail="Task is not associated with any project")
 
    task.status = status
    await db.commit()
    await db.refresh(task)
    
    logger.info(f"Task ID {task.id} status updated to '{status}' for intern ID {intern_id} by user ID {user.id}")
    return task
    