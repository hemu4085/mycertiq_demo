# backend/app/api/routes/ask_cme.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.ask_cme import AskCMERequest, AskCMEResponse
from app.services.cme_query import run_cme_query

router = APIRouter(tags=["ask"])


@router.post("/cme", response_model=AskCMEResponse)
async def ask_cme(
    payload: AskCMERequest,
    db: Session = Depends(get_db),
) -> AskCMEResponse:
    """
    Human-like, personalized CME query endpoint.
    """
    try:
        answer, recommendations = await run_cme_query(
            request=payload,
            db=db,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Error while processing CME question: {exc}",
        )

    return AskCMEResponse(
        question=payload.question,
        answer=answer,
        recommendations=recommendations,
    )
