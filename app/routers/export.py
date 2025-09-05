from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.models.leave import Leave
from app.models.user import User
from app.models.role import Role
from app.core.auth import get_current_user
from app.models.user import User as UserModel
import csv
import io
from typing import List
from datetime import datetime
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/export", tags=["Export"])

@router.get("/leaves-csv")
async def export_leaves_csv(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    result = await db.execute(
        select(Leave).options(selectinload(Leave.user))
    )
    leaves = result.scalars().all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'Leave ID', 'User ID', 'User Name', 'Start Date', 'End Date', 
        'Status', 'Reason', 'Created At', 'Updated At'
    ])
    for leave in leaves:
        writer.writerow([
            leave.id,
            leave.user_id,
            leave.user.full_name if leave.user else 'N/A',
            leave.start_date,
            leave.end_date,
            leave.status,
            leave.reason,
            leave.created_at,
            leave.updated_at
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=leaves_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


@router.get("/users-csv")
async def export_users_csv(
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    result = await db.execute(select(User).options(selectinload(User.role)))
    users = result.scalars().all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow([
        'User ID', 'Email', 'Full Name', 'Phone', 'Role ID', 'Role Name'
    ])
    
    for user in users:
        writer.writerow([
            user.id,
            user.email,
            user.full_name,
            user.phone,
            user.role_id,
            user.role.name if user.role else 'N/A'
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    ) 