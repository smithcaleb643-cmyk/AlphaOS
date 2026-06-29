from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime

from database.memory import Base


class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)

    coin_name = Column(String, index=True)

    liquidity = Column(Float, default=0)
    volume = Column(Float, default=0)
    market_cap = Column(Float, default=0)
    holder_count = Column(Integer, default=0)
    age_minutes = Column(Integer, default=0)
    price_change = Column(Float, default=0)

    score = Column(Integer)
    risk_score = Column(Integer, default=0)
    probability = Column(Float, default=0)

    action = Column(String)
    status = Column(String, default="scanned")
    reason = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)