from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import (
    NotificationCreate, 
    NotificationUpdate, 
    NotificationResponse
)
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("/", response_model=List[NotificationResponse])
async def get_user_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
    )
    notifications = result.scalars().all()
    return notifications

@router.post("/", response_model=NotificationResponse)
async def create_notification(
    notification: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if notification.user_id != current_user.id and current_user.role.name not in ["Admin", "Manager"]:
        raise HTTPException(status_code=403, detail="Can only create notifications for yourself")
    
    db_notification = Notification(**notification.dict())
    db.add(db_notification)
    await db.commit()
    await db.refresh(db_notification)
    
    logger.info(f"Notification created for user ID {notification.user_id} by user ID {current_user.id}")
    return db_notification

@router.patch("/{notification_id}", response_model=NotificationResponse)
async def update_notification(
    notification_id: int,
    notification_update: NotificationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    db_notification = result.scalar_one_or_none()
    
    if not db_notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    if db_notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this notification")
    
    update_data = notification_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_notification, field, value)
    
    await db.commit()
    await db.refresh(db_notification)
    
    logger.info(f"Notification ID {notification_id} updated by user ID {current_user.id}")
    return db_notification

@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    db_notification = result.scalar_one_or_none()
    
    if not db_notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    if db_notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this notification")
    
    await db.delete(db_notification)
    await db.commit()
    
    logger.info(f"Notification ID {notification_id} deleted by user ID {current_user.id}")
    return {"message": "Notification deleted successfully"}
