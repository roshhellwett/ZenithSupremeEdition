import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from core.config import DATABASE_URL, DB_POOL_SIZE
from zenith_crypto_bot.models import CryptoBase, Subscription, ActivationKey, CryptoUser

engine = create_async_engine(DATABASE_URL, pool_size=DB_POOL_SIZE)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_crypto_db():
    async with engine.begin() as conn:
        await conn.run_sync(CryptoBase.metadata.create_all)

class SubscriptionRepo:

    @staticmethod
    async def register_user(user_id: int):
        async with AsyncSessionLocal() as session:
            stmt = pg_insert(CryptoUser).values(user_id=user_id, alerts_enabled=False).on_conflict_do_nothing()
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def toggle_alerts(user_id: int, enable: bool):
        async with AsyncSessionLocal() as session:
            stmt = pg_insert(CryptoUser).values(user_id=user_id, alerts_enabled=enable).on_conflict_do_update(
                index_elements=['user_id'], set_=dict(alerts_enabled=enable)
            )
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def get_alert_subscribers():
        """Returns tuple: (list_of_free_users, list_of_pro_users)"""
        async with AsyncSessionLocal() as session:
            now = datetime.now(timezone.utc)
            
            # Get all users with alerts enabled
            users_res = await session.execute(select(CryptoUser.user_id).where(CryptoUser.alerts_enabled == True))
            all_alert_users = set([r[0] for r in users_res.all()])
            
            # Get all active pro users
            pro_res = await session.execute(select(Subscription.user_id).where(Subscription.expires_at > now))
            all_pro_users = set([r[0] for r in pro_res.all()])
            
            pro_subscribers = list(all_alert_users.intersection(all_pro_users))
            free_subscribers = list(all_alert_users.difference(all_pro_users))
            
            return free_subscribers, pro_subscribers

    @staticmethod
    async def generate_key(days: int) -> str:
        new_key = f"ZENITH-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:4].upper()}"
        async with AsyncSessionLocal() as session:
            session.add(ActivationKey(key_string=new_key, duration_days=days))
            await session.commit()
        return new_key

    @staticmethod
    async def redeem_key(user_id: int, key_string: str) -> tuple[bool, str]:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                res = await session.execute(select(ActivationKey).where(ActivationKey.key_string == key_string).with_for_update())
                key = res.scalar_one_or_none()
                
                if not key or key.is_used: 
                    return False, "❌ <b>Activation Failed:</b> Invalid or already used key."
                
                key.is_used = True
                key.used_by = user_id
                
                res = await session.execute(select(Subscription).where(Subscription.user_id == user_id).with_for_update())
                sub = res.scalar_one_or_none()
                
                now = datetime.now(timezone.utc)
                add_on = timedelta(days=key.duration_days)
                
                if sub and sub.expires_at > now:
                    sub.expires_at += add_on 
                else:
                    new_expiry = now + add_on
                    if sub: sub.expires_at = new_expiry
                    else: session.add(Subscription(user_id=user_id, expires_at=new_expiry))
                    
                return True, f"💎 <b>ZENITH PRO ACTIVATED</b>\n\n✅ Successfully applied <b>{key.duration_days} days</b> to your account.\nEnjoy zero-latency intelligence."

    @staticmethod
    async def get_days_left(user_id: int) -> int:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
            sub = res.scalar_one_or_none()
            
            now = datetime.now(timezone.utc)
            if not sub or sub.expires_at < now:
                return 0
            return (sub.expires_at - now).days

async def dispose_crypto_engine():
    await engine.dispose()