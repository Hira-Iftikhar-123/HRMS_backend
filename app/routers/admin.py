from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.core.auth import require_roles
from app.models.admin_log import AdminLog
from app.schemas.admin_log import AdminLogResponse


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/logs", response_model=List[AdminLogResponse])
async def get_admin_logs(
	type: Optional[str] = Query(None, description="Filter by log type"),
	from_datetime: Optional[str] = Query(None, alias="from", description="ISO datetime inclusive"),
	to_datetime: Optional[str] = Query(None, alias="to", description="ISO datetime inclusive"),
	db: AsyncSession = Depends(get_db),
	user=Depends(require_roles(["Admin", "Manager", "HR"]))
):
	query = select(AdminLog)

	if type:
		query = query.where(AdminLog.type == type)

	# Parse datetimes if provided
	def _parse(dt_str: Optional[str]) -> Optional[datetime]:
		if not dt_str:
			return None
		try:
			return datetime.fromisoformat(dt_str)
		except ValueError:
			return None

	start_dt = _parse(from_datetime)
	end_dt = _parse(to_datetime)
	if start_dt:
		query = query.where(AdminLog.created_at >= start_dt)
	if end_dt:
		# include the entire second by adding a tiny delta
		query = query.where(AdminLog.created_at <= end_dt + timedelta(microseconds=1))

	query = query.order_by(AdminLog.created_at.desc())
	result = await db.execute(query)
	return result.scalars().all()


