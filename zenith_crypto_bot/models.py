from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Integer, Float, UniqueConstraint
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

CryptoBase = declarative_base()

class CryptoUser(CryptoBase):
    __tablename__ = "crypto_users"
    user_id = Column(BigInteger, primary_key=True)
    alerts_enabled = Column(Boolean, default=False)
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Subscription(CryptoBase):
    __tablename__ = "crypto_subscriptions"
    user_id = Column(BigInteger, primary_key=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ActivationKey(CryptoBase):
    __tablename__ = "crypto_activation_keys"
    key_string = Column(String(50), primary_key=True)
    duration_days = Column(Integer, nullable=False)
    is_used = Column(Boolean, default=False)
    used_by = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class SavedAudit(CryptoBase):
    __tablename__ = "crypto_saved_audits"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    contract = Column(String(150), nullable=False)
    saved_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint('user_id', 'contract', name='uix_user_contract'),)

# ==========================================
# 💎 PRO FEATURE MODELS
# ==========================================

class PriceAlert(CryptoBase):
    """Stores user price alerts for any CoinGecko-supported token."""
    __tablename__ = "crypto_price_alerts"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    token_id = Column(String(100), nullable=False)       # CoinGecko ID (e.g. "bitcoin")
    token_symbol = Column(String(20), nullable=False)     # Display symbol (e.g. "BTC")
    target_price = Column(Float, nullable=False)
    direction = Column(String(10), nullable=False)        # "above" or "below"
    is_triggered = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class TrackedWallet(CryptoBase):
    """Stores wallet addresses that Pro users want to monitor for transactions."""
    __tablename__ = "crypto_tracked_wallets"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    wallet_address = Column(String(100), nullable=False)
    label = Column(String(50), default="Unnamed Wallet")
    last_checked_tx = Column(String(100), nullable=True)  # Last known tx hash to avoid dupes
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint('user_id', 'wallet_address', name='uix_user_wallet'),)

class WatchlistToken(CryptoBase):
    """Stores user's portfolio watchlist with entry prices for P&L calculation."""
    __tablename__ = "crypto_watchlist"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, index=True, nullable=False)
    token_id = Column(String(100), nullable=False)        # CoinGecko ID
    token_symbol = Column(String(20), nullable=False)
    entry_price = Column(Float, nullable=False)
    quantity = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (UniqueConstraint('user_id', 'token_id', name='uix_user_watchlist_token'),)