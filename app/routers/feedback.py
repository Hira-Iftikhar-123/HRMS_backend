from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import Optional, List
import os
import shutil
from datetime import datetime
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.feedback import Feedback
from app.models.project import Project
from app.models.user import User
from app.models.project_assignment import ProjectAssignment
from app.schemas.feedback import FeedbackResponse
from app.models.admin_log import AdminLog
from app.core.notifications import create_system_notification
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/feedback", tags=["Feedback"])

UPLOAD_DIR = "uploads/feedback"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def _is_pm_or_manager(user: User) -> bool:
    return user.role and user.role.name and user.role.name.lower() in {"pm", "manager", "admin"}

@router.post("/submit_feedback", response_model=FeedbackResponse)
async def submit_feedback(
    project_id: int = Form(...),
    intern_id: int = Form(...),
    pm_id: int = Form(...),
    feedback_text: str = Form(...),
    rating: int = Form(...),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):  
    if not 1 <= rating <= 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    # Check if current user is PM/Manager/Admin
    if current_user.role.name not in ["PM", "Manager", "Admin"]:
        raise HTTPException(status_code=403, detail="Only PMs, Managers, and Admins can submit feedback")
    
    # Validate PM exists and has PM role
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.id == pm_id)
    )
    pm_user = result.scalar_one_or_none()
    if not pm_user:
        raise HTTPException(status_code=404, detail="PM not found")
    if not pm_user.role or pm_user.role.name != "PM":
        raise HTTPException(status_code=400, detail="Specified user is not a PM")
    
    # Validate project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Validate intern exists and is assigned to the project
    result = await db.execute(
        select(ProjectAssignment).where(
            ProjectAssignment.intern_id == intern_id,
            ProjectAssignment.project_id == project_id
        )
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=400, detail="Intern is not assigned to this project")
    
    file_path = None
    if file:
        # Validate file type
        allowed_extensions = {'.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png'}
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(status_code=400, detail="Invalid file type. Allowed: PDF, DOC, DOCX, TXT, JPG, PNG")
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"feedback_{project_id}_{intern_id}_{timestamp}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        # Save file
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            raise HTTPException(status_code=500, detail="Failed to save uploaded file")
    
    feedback = Feedback(
        project_id=project_id,
        intern_id=intern_id,
        pm_id=pm_id,
        feedback_text=feedback_text,
        rating=rating,
        file_path=file_path
    )
    
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)
    
    # Create notification for the intern
    try:
        await create_system_notification(
            db=db,
            user_id=intern_id,
            title="New Feedback Received",
            message=f"You have received new feedback for project '{project.name}' with rating {rating}/5",
            notification_type="feedback"
        )
    except Exception as e:
        logger.warning(f"Failed to create notification: {e}")
        # Don't fail the feedback submission if notification fails
    
    logger.info(f"Feedback submitted for intern ID {intern_id} on project ID {project_id} by PM ID {pm_id}")
    # Write admin log
    try:
        db.add(AdminLog(
            type="feedback",
            message="Feedback submitted",
            actor_user_id=current_user.id,
            meta={
                "project_id": project_id,
                "intern_id": intern_id,
                "pm_id": pm_id,
                "rating": rating
            }
        ))
        await db.commit()
    except Exception:
        logger.exception("Failed to write admin log for feedback submission")
    
    return feedback

@router.get("/history/{intern_id}", response_model=List[FeedbackResponse])
async def get_feedback_history(
    intern_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not _is_pm_or_manager(current_user):
        raise HTTPException(status_code=403, detail="Only PM/Manager/Admin can view feedback history")
    
    result = await db.execute(
        select(Feedback).where(Feedback.intern_id == intern_id).order_by(Feedback.created_at.desc())
    )
    if current_user.id == intern_id:
        result = await db.execute(
            select(Feedback).where(Feedback.intern_id == intern_id).order_by(Feedback.created_at.desc())
        )
    else:
        raise HTTPException(status_code=403, detail="Only PM/Manager/Admin can see intern's feedback history")
    feedbacks = result.scalars().all()
    return feedbacks