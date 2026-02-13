import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import DATABASE_URL, DB_POOL_SIZE, DB_MAX_OVERFLOW

logger = logging.getLogger("DATABASE")

# =================================================================
# POSTGRESQL CONNECTION POOL
# Optimized for Railway 'Starter' Plan limitations.
# =================================================================
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=DB_POOL_SIZE,        # Limit active connections (Default: 5)
    max_overflow=DB_MAX_OVERFLOW,  # Allowed burst connections (Default: 10)
    pool_timeout=30,               # Wait 30s for a slot before crashing
    pool_pre_ping=True,            # Auto-detect and restart dead connections
    pool_recycle=1800              # Recycle connections every 30 mins
)

AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False,
    autoflush=False
)

Base = declarative_base()

logger.info("✅ DATABASE: PostgreSQL High-Performance Pool Initialized")
#@academictelebotbyroshhellwett