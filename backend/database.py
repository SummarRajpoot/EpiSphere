import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

# Load .env from the current directory or Backend folder
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL or "user:password" in DATABASE_URL:
    DATABASE_URL = "sqlite+aiosqlite:///./outbreakiq.db"
else:
    # Use psycopg (v3) instead of asyncpg for 3.14 compatibility
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,  # Recycle connections every 5 minutes to avoid Neon suspending them
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
