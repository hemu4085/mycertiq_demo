
# backend/app/models/cme_event.py

from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, Numeric, TIMESTAMP
from app.database import Base

class CMEEvent(Base):
    __tablename__ = "cme_event"

    id = Column(BigInteger, primary_key=True, index=True)
    external_id = Column(String(255))
    title = Column(String(500), nullable=False)
    description = Column(Text)
    format_id = Column(BigInteger)
    credit_type = Column(String(255))
    max_credits = Column(Numeric(6, 2))
    url = Column(Text)
    location_id = Column(BigInteger)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True))
    credits = Column(Numeric)
    provider_name = Column(Text)
    format = Column(Text)
    audience = Column(Text)
