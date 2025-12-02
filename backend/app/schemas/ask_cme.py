# app/schemas/ask_cme.py

from typing import List, Optional
from pydantic import BaseModel


class AskCMERequest(BaseModel):
    """Incoming payload for the human-like CME question."""
    question: str

    # Personalization hooks
    physician_id: Optional[int] = None

    # Optional explicit overrides (used if present, else DB or ignored)
    specialty: Optional[str] = None          # e.g., "Anesthesiology"
    state: Optional[str] = None              # e.g., "MA"
    preferred_format: Optional[str] = None   # "online", "live", "hybrid"
    min_credits: Optional[float] = None
    credit_type: Optional[str] = None        # "AMA", "MOC II", "Ethics", etc.
    travel_ok: Optional[bool] = None         # True = willing to travel


class CMERecommendation(BaseModel):
    """Single recommended CME item."""
    cme_event_id: int
    title: str
    provider: Optional[str] = None
    credit_hours: Optional[float] = None
    url: Optional[str] = None

    # Optional, but useful for UI
    score: Optional[float] = None  # higher is better
    rank: int
    reason: Optional[str] = None   # short human-readable explanation


class AskCMEResponse(BaseModel):
    """Response: natural-language answer + ranked CME list."""
    question: str
    answer: str
    recommendations: List[CMERecommendation]
