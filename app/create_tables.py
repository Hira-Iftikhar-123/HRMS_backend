import asyncio
from app.core.database import Base, engine
from app.models import *  # Import all models to register them

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(create_tables())