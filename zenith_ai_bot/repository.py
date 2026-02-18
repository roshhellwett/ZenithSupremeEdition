from datetime import datetime, timezone, date
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete, func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.config import DATABASE_URL, DB_POOL_SIZE
from zenith_ai_bot.models import AIBase, AIConversation, AIUsageLog
from core.logger import setup_logger

logger = setup_logger("AI_REPO")

engine = create_async_engine(
    DATABASE_URL,
    pool_size=DB_POOL_SIZE,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={
        "ssl": True,
        "connect_timeout": 10,
        "command_timeout": 30,
    }
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_ai_db():
    async with engine.begin() as conn:
        await conn.run_sync(AIBase.metadata.create_all)


async def dispose_ai_engine():
    await engine.dispose()


class ConversationRepo:

    @staticmethod
    async def add_message(user_id: int, role: str, content: str):
        async with AsyncSessionLocal() as session:
            session.add(AIConversation(user_id=user_id, role=role, content=content[:2000]))
            await session.commit()

    @staticmethod
    async def get_history(user_id: int, limit: int = 10) -> list:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(AIConversation)
                .where(AIConversation.user_id == user_id)
                .order_by(AIConversation.created_at.desc())
                .limit(limit)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return list(reversed(rows))

    @staticmethod
    async def clear_history(user_id: int) -> int:
        async with AsyncSessionLocal() as session:
            stmt = delete(AIConversation).where(AIConversation.user_id == user_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount

    @staticmethod
    async def count_messages(user_id: int) -> int:
        async with AsyncSessionLocal() as session:
            stmt = select(func.count()).select_from(AIConversation).where(AIConversation.user_id == user_id)
            return (await session.execute(stmt)).scalar() or 0


class UsageRepo:

    @staticmethod
    async def _get_or_create(session, user_id: int) -> AIUsageLog:
        today = date.today()
        stmt = select(AIUsageLog).where(AIUsageLog.user_id == user_id, AIUsageLog.usage_date == today)
        row = (await session.execute(stmt)).scalar_one_or_none()
        if not row:
            row = AIUsageLog(user_id=user_id, usage_date=today, query_count=0, summarize_count=0)
            session.add(row)
            await session.flush()
        return row

    @staticmethod
    async def increment_queries(user_id: int) -> int:
        async with AsyncSessionLocal() as session:
            row = await UsageRepo._get_or_create(session, user_id)
            row.query_count += 1
            await session.commit()
            return row.query_count

    @staticmethod
    async def increment_summarize(user_id: int) -> int:
        async with AsyncSessionLocal() as session:
            row = await UsageRepo._get_or_create(session, user_id)
            row.summarize_count += 1
            await session.commit()
            return row.summarize_count

    @staticmethod
    async def get_today_usage(user_id: int) -> dict:
        async with AsyncSessionLocal() as session:
            row = await UsageRepo._get_or_create(session, user_id)
            return {
                "queries": row.query_count,
                "summarizes": row.summarize_count,
                "persona": row.persona or "default",
            }

    @staticmethod
    async def set_persona(user_id: int, persona: str):
        async with AsyncSessionLocal() as session:
            row = await UsageRepo._get_or_create(session, user_id)
            row.persona = persona
            await session.commit()

    @staticmethod
    async def get_persona(user_id: int) -> str:
        async with AsyncSessionLocal() as session:
            row = await UsageRepo._get_or_create(session, user_id)
            return row.persona or "default"
