from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import SessionLocal
from app.models.role import Role
import app.schemas.role as role_schemas
from typing import List

router = APIRouter(
    prefix="/roles",
    tags=["roles"]
)

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.get("/get-roles", response_model=List[role_schemas.RoleResponse])
async def get_roles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Role))
    roles = result.scalars().all()
    return roles 