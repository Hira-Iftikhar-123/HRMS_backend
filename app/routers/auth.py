from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import SessionLocal
from app.models.user import User
import app.schemas.token as token_schemas
from app.core.auth import verify_password, create_access_token

router = APIRouter(
    tags=["auth"]
)

async def get_db():
    async with SessionLocal() as session:
        yield session

@router.post("/login", response_model=token_schemas.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user_obj = result.scalar_one_or_none()
    if not user_obj or not verify_password(form_data.password, user_obj.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user_obj.username})
    return {"access_token": access_token, "token_type": "bearer"} 