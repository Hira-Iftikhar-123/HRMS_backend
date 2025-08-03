from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.core.auth import get_current_user, require_roles
from app.models.leave import Leave
from sqlalchemy.future import select
from app.schemas.leave import LeaveResponse, LeaveUpdate
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/leave", tags=["Leave"])


@router.get("/all", response_model=List[LeaveResponse])
async def get_all_leaves(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles(["admin", "hr"]))
):
    result = await db.execute(select(Leave))
    leaves = result.scalars().all()
    return leaves

@router.patch("/update-status", response_model=LeaveResponse)
async def update_leave_status(
    leave_id: int,
    update: LeaveUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles(["admin", "hr"]))
):
    result = await db.execute(select(Leave).where(Leave.id == leave_id))
    leave = result.scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")

    leave.status = update.status
    await db.commit()
    await db.refresh(leave)
    logger.info(f"Leave ID {leave.id} status updated to '{leave.status}' by {user.username}")
    return leave
