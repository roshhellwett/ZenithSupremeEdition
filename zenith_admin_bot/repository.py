from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from core.config import DATABASE_URL, DB_POOL_SIZE
from core.logger import setup_logger
from zenith_admin_bot.models import AdminAuditLog, BotRegistry, ActionType, BotStatus, AdminBase

logger = setup_logger("ADMIN_DB")

engine = create_async_engine(DATABASE_URL, pool_size=DB_POOL_SIZE, max_overflow=5, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_admin_db():
    async with engine.begin() as conn:
        await conn.run_sync(AdminBase.metadata.create_all)
    logger.info("✅ Admin DB initialized")


class AdminRepo:

    @staticmethod
    async def log_action(
        admin_user_id: int,
        action: ActionType,
        target_user_id: Optional[int] = None,
        details: Optional[str] = None,
    ):
        async with AsyncSessionLocal() as session:
            log_entry = AdminAuditLog(
                admin_user_id=admin_user_id,
                action=action,
                target_user_id=target_user_id,
                details=details,
            )
            session.add(log_entry)
            await session.commit()

    @staticmethod
    async def get_audit_trail(limit: int = 20) -> list:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(AdminAuditLog)
                .order_by(AdminAuditLog.created_at.desc())
                .limit(limit)
            )
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_audit_for_user(user_id: int, limit: int = 20) -> list:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(AdminAuditLog)
                .where(AdminAuditLog.target_user_id == user_id)
                .order_by(AdminAuditLog.created_at.desc())
                .limit(limit)
            )
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_audit_by_action(action: ActionType, limit: int = 20) -> list:
        async with AsyncSessionLocal() as session:
            stmt = (
                select(AdminAuditLog)
                .where(AdminAuditLog.action == action)
                .order_by(AdminAuditLog.created_at.desc())
                .limit(limit)
            )
            return (await session.execute(stmt)).scalars().all()


class BotRegistryRepo:

    @staticmethod
    async def register_bot(bot_name: str, token_hash: Optional[str] = None) -> BotRegistry:
        async with AsyncSessionLocal() as session:
            stmt = select(BotRegistry).where(BotRegistry.bot_name == bot_name)
            existing = (await session.execute(stmt)).scalar_one_or_none()

            if existing:
                existing.token_hash = token_hash
                existing.status = BotStatus.ACTIVE
                existing.registered_at = datetime.utcnow()
                await session.commit()
                return existing
            else:
                new_bot = BotRegistry(
                    bot_name=bot_name,
                    token_hash=token_hash,
                    status=BotStatus.ACTIVE,
                )
                session.add(new_bot)
                await session.commit()
                await session.refresh(new_bot)
                return new_bot

    @staticmethod
    async def unregister_bot(bot_name: str):
        async with AsyncSessionLocal() as session:
            stmt = select(BotRegistry).where(BotRegistry.bot_name == bot_name)
            bot = (await session.execute(stmt)).scalar_one_or_none()
            if bot:
                bot.status = BotStatus.INACTIVE
                await session.commit()

    @staticmethod
    async def get_all_bots() -> list:
        async with AsyncSessionLocal() as session:
            stmt = select(BotRegistry).order_by(BotRegistry.registered_at.desc())
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_bot_by_name(bot_name: str) -> Optional[BotRegistry]:
        async with AsyncSessionLocal() as session:
            stmt = select(BotRegistry).where(BotRegistry.bot_name == bot_name)
            return (await session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def update_health_status(bot_name: str, status: str):
        async with AsyncSessionLocal() as session:
            stmt = select(BotRegistry).where(BotRegistry.bot_name == bot_name)
            bot = (await session.execute(stmt)).scalar_one_or_none()
            if bot:
                bot.last_health_check = datetime.utcnow()
                bot.health_status = status
                if status == "error":
                    bot.status = BotStatus.ERROR
                await session.commit()


class MonitoringRepo:

    @staticmethod
    async def get_subscription_stats() -> dict:
        from zenith_crypto_bot.repository import SubscriptionRepo

        async with AsyncSessionLocal() as session:
            from zenith_crypto_bot.models import Subscription, CryptoUser
            from sqlalchemy import func

            total_users_res = await session.execute(select(func.count(CryptoUser.user_id)))
            total_users = total_users_res.scalar() or 0

            now = datetime.now(timezone.utc)
            pro_users_res = await session.execute(
                select(func.count(Subscription.user_id)).where(Subscription.expires_at > now)
            )
            pro_users = pro_users_res.scalar() or 0

            active_subs_res = await session.execute(
                select(func.count(Subscription.user_id)).where(Subscription.expires_at > now)
            )
            active_subs = active_subs_res.scalar() or 0

            expiring_soon_res = await session.execute(
                select(func.count(Subscription.user_id)).where(
                    Subscription.expires_at > now,
                    Subscription.expires_at <= now + timedelta(days=7)
                )
            )
            expiring_soon = expiring_soon_res.scalar() or 0

            return {
                "total_users": total_users,
                "pro_users": pro_users,
                "free_users": total_users - pro_users,
                "active_subscriptions": active_subs,
                "expiring_within_7_days": expiring_soon,
            }

    @staticmethod
    async def get_ticket_stats() -> dict:
        from zenith_support_bot.repository import TicketRepo

        try:
            return await TicketRepo.get_ticket_stats()
        except Exception:
            return {"total": 0, "open": 0, "in_progress": 0, "resolved": 0, "closed": 0}

    @staticmethod
    async def get_all_active_subscriptions() -> list:
        from zenith_crypto_bot.models import Subscription

        async with AsyncSessionLocal() as session:
            now = datetime.now(timezone.utc)
            stmt = (
                select(Subscription)
                .where(Subscription.expires_at > now)
                .order_by(Subscription.expires_at.asc())
            )
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_recent_keys(limit: int = 10) -> list:
        from zenith_crypto_bot.models import ActivationKey

        async with AsyncSessionLocal() as session:
            stmt = (
                select(ActivationKey)
                .where(ActivationKey.is_used == False)
                .order_by(ActivationKey.created_at.desc())
                .limit(limit)
            )
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_user_subscription_details(user_id: int) -> dict:
        from zenith_crypto_bot.models import Subscription

        async with AsyncSessionLocal() as session:
            stmt = select(Subscription).where(Subscription.user_id == user_id)
            sub = (await session.execute(stmt)).scalar_one_or_none()

            if not sub:
                return {"has_subscription": False, "days_left": 0, "expires_at": None}

            now = datetime.now(timezone.utc)
            if sub.expires_at <= now:
                return {"has_subscription": False, "days_left": 0, "expires_at": sub.expires_at}

            days_left = (sub.expires_at - now).days
            return {
                "has_subscription": True,
                "days_left": days_left,
                "expires_at": sub.expires_at,
            }


async def dispose_admin_engine():
    await engine.dispose()
