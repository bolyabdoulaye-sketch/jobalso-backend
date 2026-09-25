"""
Moteur de base de données et fabrique de sessions SQLAlchemy 2.0.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # évite les connexions mortes après une inactivité longue
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    future=True,
)

# Session utilisée par les dépendances FastAPI async (app.deps.get_db).
async_engine = create_async_engine(settings.async_database_url, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(
    async_engine, expire_on_commit=False, class_=AsyncSession
)
