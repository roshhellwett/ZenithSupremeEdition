import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from core.config import DATABASE_URL, DB_POOL_SIZE
from zenith_crypto_bot.models import (
    CryptoBase, Subscription, ActivationKey, CryptoUser, SavedAudit,
    PriceAlert, TrackedWallet, WatchlistToken
)

engine = create_async_engine(DATABASE_URL, pool_size=DB_POOL_SIZE, pool_pre_ping=True)
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
        async with AsyncSessionLocal() as session:
            now = datetime.now(timezone.utc)
            users_res = await session.execute(select(CryptoUser.user_id).where(CryptoUser.alerts_enabled == True))
            all_alert_users = set([r[0] for r in users_res.all()])
            
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
            if not sub or sub.expires_at <= now:
                return 0
            remaining = sub.expires_at - now
            # Round up so users with <24h left still show "1 day" and stay Pro
            return remaining.days + (1 if remaining.seconds > 0 else 0)

    @staticmethod
    async def is_pro(user_id: int) -> bool:
        """Check if user has any active Pro time remaining (down to the second)."""
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
            sub = res.scalar_one_or_none()
            if not sub:
                return False
            return sub.expires_at > datetime.now(timezone.utc)

    @staticmethod
    async def extend_subscription(user_id: int, days: int = 30) -> tuple[bool, str]:
        """Admin renewal: add days to a user's subscription without a new key."""
        async with AsyncSessionLocal() as session:
            async with session.begin():
                res = await session.execute(
                    select(Subscription).where(Subscription.user_id == user_id).with_for_update()
                )
                sub = res.scalar_one_or_none()
                now = datetime.now(timezone.utc)
                add_on = timedelta(days=days)

                if sub:
                    # If still active, extend from current expiry; otherwise from now
                    base = sub.expires_at if sub.expires_at > now else now
                    sub.expires_at = base + add_on
                else:
                    session.add(Subscription(user_id=user_id, expires_at=now + add_on))

                new_expiry = (sub.expires_at if sub else now + add_on)
                return True, (
                    f"✅ <b>Subscription Extended</b>\n\n"
                    f"<b>User:</b> <code>{user_id}</code>\n"
                    f"<b>Added:</b> {days} days\n"
                    f"<b>New Expiry:</b> {new_expiry.strftime('%d %b %Y %H:%M UTC')}"
                )

    @staticmethod
    async def get_expiring_users(within_hours: int = 72) -> list:
        """Get users whose subscription expires within N hours (for warnings)."""
        async with AsyncSessionLocal() as session:
            now = datetime.now(timezone.utc)
            cutoff = now + timedelta(hours=within_hours)
            stmt = select(Subscription).where(
                Subscription.expires_at > now,
                Subscription.expires_at <= cutoff
            )
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_just_expired_users(within_hours: int = 1) -> list:
        """Get users whose subscription expired within the last N hours."""
        async with AsyncSessionLocal() as session:
            now = datetime.now(timezone.utc)
            cutoff = now - timedelta(hours=within_hours)
            stmt = select(Subscription).where(
                Subscription.expires_at <= now,
                Subscription.expires_at >= cutoff
            )
            return (await session.execute(stmt)).scalars().all()

    # --- 🗂️ AUDIT VAULT ---
    @staticmethod
    async def save_audit(user_id: int, contract: str):
        async with AsyncSessionLocal() as session:
            stmt = pg_insert(SavedAudit).values(
                user_id=user_id, contract=contract[:100]
            ).on_conflict_do_update(
                index_elements=['user_id', 'contract'],
                set_=dict(saved_at=datetime.now(timezone.utc))
            )
            await session.execute(stmt)
            count_stmt = select(SavedAudit).where(SavedAudit.user_id == user_id).order_by(SavedAudit.saved_at.desc())
            audits = (await session.execute(count_stmt)).scalars().all()
            if len(audits) > 10:
                for extra_audit in audits[10:]:
                    await session.delete(extra_audit)
            await session.commit()

    @staticmethod
    async def get_saved_audits(user_id: int):
        async with AsyncSessionLocal() as session:
            stmt = select(SavedAudit).where(SavedAudit.user_id == user_id).order_by(SavedAudit.saved_at.desc())
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_audit_by_id(user_id: int, audit_id: int):
        async with AsyncSessionLocal() as session:
            stmt = select(SavedAudit).where(SavedAudit.user_id == user_id, SavedAudit.id == audit_id)
            return (await session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    async def delete_audit(user_id: int, audit_id: int):
        async with AsyncSessionLocal() as session:
            stmt = delete(SavedAudit).where(SavedAudit.user_id == user_id, SavedAudit.id == audit_id)
            await session.execute(stmt)
            await session.commit()

    @staticmethod
    async def clear_all_audits(user_id: int):
        async with AsyncSessionLocal() as session:
            stmt = delete(SavedAudit).where(SavedAudit.user_id == user_id)
            await session.execute(stmt)
            await session.commit()


# ==========================================
# 💎 PRO FEATURE REPOSITORIES
# ==========================================

class PriceAlertRepo:

    @staticmethod
    async def create_alert(user_id: int, token_id: str, token_symbol: str, target_price: float, direction: str) -> PriceAlert:
        async with AsyncSessionLocal() as session:
            alert = PriceAlert(
                user_id=user_id, token_id=token_id, token_symbol=token_symbol.upper(),
                target_price=target_price, direction=direction
            )
            session.add(alert)
            await session.commit()
            await session.refresh(alert)
            return alert

    @staticmethod
    async def get_user_alerts(user_id: int) -> list:
        async with AsyncSessionLocal() as session:
            stmt = select(PriceAlert).where(
                PriceAlert.user_id == user_id, PriceAlert.is_triggered == False
            ).order_by(PriceAlert.created_at.desc())
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_all_active_alerts() -> list:
        async with AsyncSessionLocal() as session:
            stmt = select(PriceAlert).where(PriceAlert.is_triggered == False)
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def trigger_alert(alert_id: int):
        async with AsyncSessionLocal() as session:
            stmt = select(PriceAlert).where(PriceAlert.id == alert_id)
            alert = (await session.execute(stmt)).scalar_one_or_none()
            if alert:
                alert.is_triggered = True
                await session.commit()

    @staticmethod
    async def delete_alert(user_id: int, alert_id: int) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = delete(PriceAlert).where(PriceAlert.user_id == user_id, PriceAlert.id == alert_id)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def count_user_alerts(user_id: int) -> int:
        async with AsyncSessionLocal() as session:
            stmt = select(PriceAlert).where(
                PriceAlert.user_id == user_id, PriceAlert.is_triggered == False
            )
            return len((await session.execute(stmt)).scalars().all())


class WalletTrackerRepo:

    @staticmethod
    async def add_wallet(user_id: int, wallet_address: str, label: str = "Unnamed Wallet") -> bool:
        async with AsyncSessionLocal() as session:
            stmt = pg_insert(TrackedWallet).values(
                user_id=user_id, wallet_address=wallet_address.lower(), label=label[:50]
            ).on_conflict_do_nothing()
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def get_user_wallets(user_id: int) -> list:
        async with AsyncSessionLocal() as session:
            stmt = select(TrackedWallet).where(TrackedWallet.user_id == user_id).order_by(TrackedWallet.created_at.desc())
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def get_all_tracked_wallets() -> list:
        """Only return wallets belonging to users with active Pro subscriptions."""
        async with AsyncSessionLocal() as session:
            now = datetime.now(timezone.utc)
            stmt = (
                select(TrackedWallet)
                .join(Subscription, TrackedWallet.user_id == Subscription.user_id)
                .where(Subscription.expires_at > now)
            )
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def remove_wallet(user_id: int, wallet_address: str) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = delete(TrackedWallet).where(
                TrackedWallet.user_id == user_id, TrackedWallet.wallet_address == wallet_address.lower()
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def update_last_tx(wallet_id: int, tx_hash: str):
        async with AsyncSessionLocal() as session:
            stmt = select(TrackedWallet).where(TrackedWallet.id == wallet_id)
            wallet = (await session.execute(stmt)).scalar_one_or_none()
            if wallet:
                wallet.last_checked_tx = tx_hash
                await session.commit()

    @staticmethod
    async def count_user_wallets(user_id: int) -> int:
        async with AsyncSessionLocal() as session:
            stmt = select(TrackedWallet).where(TrackedWallet.user_id == user_id)
            return len((await session.execute(stmt)).scalars().all())


class WatchlistRepo:

    @staticmethod
    async def add_token(user_id: int, token_id: str, token_symbol: str, entry_price: float, quantity: float = 1.0) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = pg_insert(WatchlistToken).values(
                user_id=user_id, token_id=token_id, token_symbol=token_symbol.upper(),
                entry_price=entry_price, quantity=quantity
            ).on_conflict_do_update(
                index_elements=['user_id', 'token_id'],
                set_=dict(entry_price=entry_price, quantity=quantity)
            )
            await session.execute(stmt)
            await session.commit()
            return True

    @staticmethod
    async def get_watchlist(user_id: int) -> list:
        async with AsyncSessionLocal() as session:
            stmt = select(WatchlistToken).where(WatchlistToken.user_id == user_id).order_by(WatchlistToken.created_at.desc())
            return (await session.execute(stmt)).scalars().all()

    @staticmethod
    async def remove_token(user_id: int, token_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            stmt = delete(WatchlistToken).where(
                WatchlistToken.user_id == user_id, WatchlistToken.token_id == token_id
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def count_watchlist(user_id: int) -> int:
        async with AsyncSessionLocal() as session:
            stmt = select(WatchlistToken).where(WatchlistToken.user_id == user_id)
            return len((await session.execute(stmt)).scalars().all())


async def dispose_crypto_engine():
    await engine.dispose()