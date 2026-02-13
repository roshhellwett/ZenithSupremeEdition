from sqlalchemy import Column, Integer, BigInteger, DateTime
from database.db import Base

class UserStrike(Base):
    """
    Security Table: Tracks user violations.
    """
    # FIX: Renamed table to force Railway to create a NEW one with BigInteger support
    __tablename__ = "user_strikes_v2"
    
    # Telegram IDs (BigInteger)
    user_id = Column(BigInteger, primary_key=True, index=True)
    
    strike_count = Column(Integer, default=0)
    last_violation = Column(DateTime, nullable=True)
    #@academictelebotbyroshhellwett