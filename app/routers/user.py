from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.user import User
from app.models.role import Role
from app.schemas.user import UserCreate, UserResponse
from app.core.auth import get_password_hash, require_roles, get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/user", tags=["User"])

class TokenUpdate(BaseModel):
    fcm_token: str

@router.post("/register", response_model=UserResponse)
async def register_candidate(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        # Find role by name (e.g: candidate, admin, manager, etc.)
        result = await db.execute(select(Role).filter(Role.name == user_in.role_name))
        role = result.scalar_one_or_none()
        if not role:
            raise HTTPException(status_code=400, detail="Invalid role")
        
        user = User(
            email=user_in.email,
            full_name=user_in.full_name,
            phone=user_in.phone,
            hashed_password=get_password_hash(user_in.password),
            role_id=role.id,
            fcm_token=user_in.fcm_token,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Load the role relationship for response
        result = await db.execute(
            select(User).options(selectinload(User.role)).filter(User.id == user.id)
        )
        user_with_role = result.scalar_one_or_none()
        
        return UserResponse(
            id=user_with_role.id,
            email=user_with_role.email,
            full_name=user_with_role.full_name,
            phone=user_with_role.phone,
            role=user_with_role.role.name
        )
    except IntegrityError as e:
        await db.rollback()
        if "users_email_key" in str(e):
            raise HTTPException(status_code=400, detail="Email already registered")
        else:
            raise HTTPException(status_code=400, detail="Registration failed")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/add-user", response_model=UserResponse)
async def add_user(user_in: UserCreate, db: AsyncSession = Depends(get_db), user=Depends(require_roles(["admin"]))):
    try:
        # Admin can specify role_id (e.g: 1 for admin, 2 for manager, 3 for candidate)
        if not user_in.role_id:
            raise HTTPException(status_code=400, detail="role_id required")
        
        user = User(
            email=user_in.email,
            full_name=user_in.full_name,
            phone=user_in.phone,
            hashed_password=get_password_hash(user_in.password),
            role_id=user_in.role_id,
            fcm_token=user_in.fcm_token,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Load the role relationship for response
        result = await db.execute(
            select(User).options(selectinload(User.role)).filter(User.id == user.id)
        )
        user_with_role = result.scalar_one_or_none()
        
        return UserResponse(
            id=user_with_role.id,
            email=user_with_role.email,
            full_name=user_with_role.full_name,
            phone=user_with_role.phone,
            role=user_with_role.role.name
        )
    except IntegrityError as e:
        await db.rollback()
        if "users_email_key" in str(e):
            raise HTTPException(status_code=400, detail="Email already registered")
        else:
            raise HTTPException(status_code=400, detail="User creation failed")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/get-profile", response_model=UserResponse)
async def get_user_profile(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    """Get current user's profile information"""
    try:
        result = await db.execute(
            select(User).options(selectinload(User.role)).filter(User.id == current_user.id)
        )
        user_with_role = result.scalar_one_or_none()
        
        if not user_with_role:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse(
            id=user_with_role.id,
            email=user_with_role.email,
            full_name=user_with_role.full_name,
            phone=user_with_role.phone,
            role=user_with_role.role.name
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
    
@router.post("/update-token")
async def update_fcm_token(
    token_data: TokenUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        current_user.fcm_token = token_data.fcm_token
        db.add(current_user)
        await db.commit()
        return {"message": "FCM token updated successfully"}
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update FCM token")