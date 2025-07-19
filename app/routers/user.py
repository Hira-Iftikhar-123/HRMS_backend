from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import SessionLocal
from app.models.user import User
import app.schemas.user as user_schemas
from app.core.auth import decode_access_token
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

async def get_db():
    async with SessionLocal() as session:
        yield session

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")
    username = payload["sub"]
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.username == username)
    )
    user_obj = result.scalar_one_or_none()
    if user_obj is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user_obj

@router.get("/get-profile", response_model=user_schemas.UserProfile)
async def get_profile(current_user: User = Depends(get_current_user)):
    return user_schemas.UserProfile(id=current_user.id, username=current_user.username, role=current_user.role.name) 