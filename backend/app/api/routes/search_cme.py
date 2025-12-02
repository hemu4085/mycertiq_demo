from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from openai import OpenAI
import os

from app.database import get_db  # assumes you already have this dependency

router = APIRouter(prefix="/api/cme", tags=["cme_search"])


# -----------------------------
# Pydantic response model
# -----------------------------
class CmeSearchResult(BaseModel):
    cme_id: int
    title: str
    description: str
    credit_type: Optional[str] = None
    credits: Optional[float] = None
    provider_name: Optional[str] = None
    format: Optional[str] = None
    audience: Optional[str] = None
    score: float


# -----------------------------
# Helper: OpenAI client
# -----------------------------
def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in the environment.")
    return OpenAI(api_key=api_key)


# -----------------------------
# Route: /api/cme/search
# -----------------------------
@router.get("/search", response_model=List[CmeSearchResult])
def search_cme(
    q: str = Query(..., description="Natural language search query"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    Semantic CME search using pgvector + OpenAI embeddings.

    1. Embed the query with text-embedding-3-large (1536 dims).
    2. Run vector similarity search on embedding_store.embedding.
    3. Join back to cme_event and return top-N matches.
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query 'q' must not be empty.")

    client = get_openai_client()

    # 1) Embed the query
    try:
        resp = client.embeddings.create(
            model="text-embedding-3-large",
            input=q,
            dimensions=1536,  # MUST match vector(1536) in DB
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating embedding: {e}")

    query_embedding = resp.data[0].embedding  # type: ignore

    # 2) Vector search query
    # We use cosine distance (<=>) and convert to similarity score: 1 - distance
    sql = text(
        """
        SELECT
            ce.id AS cme_id,
            ce.title,
            ce.description,
            ce.credit_type,
            ce.credits,
            ce.provider_name,
            ce.format,
            ce.audience,
            1 - (es.embedding <=> :query_embedding) AS score
        FROM embedding_store es
        JOIN cme_event ce
          ON es.source_type = 'cme_event'
         AND es.source_id = ce.id
        WHERE ce.is_active = TRUE
        ORDER BY es.embedding <=> :query_embedding
        LIMIT :limit;
        """
    )

    try:
        rows = db.execute(
            sql,
            {
                "query_embedding": query_embedding,
                "limit": limit,
            },
        ).fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error during search: {e}")

    results: List[CmeSearchResult] = []
    for row in rows:
        results.append(
            CmeSearchResult(
                cme_id=row.cme_id,
                title=row.title,
                description=row.description,
                credit_type=row.credit_type,
                credits=row.credits,
                provider_name=row.provider_name,
                format=row.format,
                audience=row.audience,
                score=float(row.score) if row.score is not None else 0.0,
            )
        )

    return results
