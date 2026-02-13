from sqlalchemy import Column, Integer, BigInteger, DateTime
from database.db import Base

class UserStrike(Base):
    """
    Security Table: Tracks user violations.
    """
    __tablename__ = "user_strikes"
    
    user_id = Column(BigInteger, primary_key=True, index=True)
    
    strike_count = Column(Integer, default=0)
    last_violation = Column(DateTime, nullable=True)
    #@academictelebotbyroshhellwett