from app.core.base import Base 
import app.models.role  
import app.models.attendance  
import app.models.project  
import app.models.task  
import app.models.leave  
import app.models.department  
import app.models.project_assignment  
import app.models.evaluation  
import app.models.hr_department_map  
import app.models.feedback  
import app.models.notification  
import app.models.admin_log  
import app.models.sync_queue  
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import asyncio
import logging
import os
from dotenv import load_dotenv
load_dotenv(override=False)

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with SessionLocal() as db:
        yield db

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)