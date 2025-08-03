from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.core.database import get_db
from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentUpdate, Department as DepartmentSchema
from app.core.auth import get_current_user
from app.models.user import User
from typing import List

router = APIRouter(prefix="/departments", tags=["Departments"])

@router.get("/", response_model=List[DepartmentSchema])
async def get_all_departments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all departments"""
    result = await db.execute(select(Department))
    departments = result.scalars().all()
    return departments

@router.get("/{department_id}", response_model=DepartmentSchema)
async def get_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific department by ID"""
    result = await db.execute(select(Department).where(Department.id == department_id))
    department = result.scalar_one_or_none()
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    return department

@router.post("/", response_model=DepartmentSchema)
async def create_department(
    department: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new department"""
    # Check if department with same name already exists
    result = await db.execute(select(Department).where(Department.name == department.name))
    existing_department = result.scalar_one_or_none()
    if existing_department:
        raise HTTPException(status_code=400, detail="Department with this name already exists")
    
    db_department = Department(**department.dict())
    db.add(db_department)
    await db.commit()
    await db.refresh(db_department)
    return db_department

@router.patch("/{department_id}", response_model=DepartmentSchema)
async def update_department(
    department_id: int,
    department_update: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a department"""
    result = await db.execute(select(Department).where(Department.id == department_id))
    db_department = result.scalar_one_or_none()
    if not db_department:
        raise HTTPException(status_code=404, detail="Department not found")
    
    # Check if name is being updated and if it conflicts with existing department
    if department_update.name and department_update.name != db_department.name:
        result = await db.execute(select(Department).where(Department.name == department_update.name))
        existing_department = result.scalar_one_or_none()
        if existing_department:
            raise HTTPException(status_code=400, detail="Department with this name already exists")
    
    # Update only provided fields
    update_data = department_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_department, field, value)
    
    await db.commit()
    await db.refresh(db_department)
    return db_department

@router.delete("/{department_id}")
async def delete_department(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a department"""
    result = await db.execute(select(Department).where(Department.id == department_id))
    db_department = result.scalar_one_or_none()
    if not db_department:
        raise HTTPException(status_code=404, detail="Department not found")
    
    await db.delete(db_department)
    await db.commit()
    return {"message": "Department deleted successfully"} 