from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
from app.core.auth import get_current_user, require_roles
from app.models.leave import Leave
from sqlalchemy.orm import selectinload
from app.core.notifications import send_firebase_notification
from app.models.admin_log import AdminLog
from sqlalchemy.future import select
from app.schemas.leave import LeaveResponse, LeaveUpdate
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/leave", tags=["Leave"])


@router.get("/all", response_model=List[LeaveResponse])
async def get_all_leaves(
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles(["Admin", "HR"]))
):
    result = await db.execute(select(Leave))
    leaves = result.scalars().all()
    return leaves

@router.patch("/update-status", response_model=LeaveResponse)
async def update_leave_status(
    leave_id: int,
    update: LeaveUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_roles(["Admin", "HR"]))
):
    result = await db.execute(
        select(Leave).options(selectinload(Leave.user)).where(Leave.id == leave_id)
    )
    leave = result.scalar_one_or_none()
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")

    leave.status = update.status
    await db.commit()
    await db.refresh(leave)
    logger.info(f"Leave ID {leave.id} status updated to '{leave.status}' by {user.email}")

    # Write admin log (non-blocking on failure)
    try:
        db.add(AdminLog(
            type="leave_status",
            message=f"Leave status updated to {leave.status}",
            actor_user_id=user.id if hasattr(user, 'id') else None,
            meta={"leave_id": leave.id, "user_id": leave.user_id, "status": leave.status}
        ))
        await db.commit()
    except Exception:
        logger.exception("Failed to write admin log for leave status update")

    # Notify the user on approval
    try:
        if leave.status.lower() == "approved" and getattr(leave.user, "fcm_token", None):
            await send_firebase_notification(
                tokens=leave.user.fcm_token,
                title="Leave Approved",
                body=f"Your leave request (ID {leave.id}) has been approved.",
            )
    except Exception:
        # Never block the response on notification failure
        logger.exception("Failed to send leave approval notification")
    return leave
