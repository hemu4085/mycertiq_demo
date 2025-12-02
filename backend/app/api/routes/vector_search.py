# backend/app/api/routes/vector_search.py

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.vector.manager import search_embeddings

router = APIRouter()


class VectorSearchRequest(BaseModel):
    query: str = Field(..., description="User's natural-language query.")
    top_k: int = Field(5, ge=1, le=50, description="Number of results to return.")
    source_type: Optional[str] = Field(
        None,
        description="Optional filter, e.g. 'cme'. If omitted, search across all sources.",
    )


class VectorSearchResult(BaseModel):
    id: int
    knowledge_chunk_id: int
    source_type: str
    source_id: Optional[int] = None
    chunk_id: Optional[str] = None
    chunk_text: str
    embedding_model: str
    score: float


@router.post(
    "/search",
    response_model=List[VectorSearchResult],
    summary="Semantic vector search over embedding_store",
)
def vector_search(
    payload: VectorSearchRequest,
    db: Session = Depends(get_db),
) -> List[VectorSearchResult]:
    """
    Perform a pgvector similarity search on embedding_store.

    - Optionally filter by source_type (e.g. 'cme')
    - Returns chunks ordered by semantic similarity.
    """
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")

    results = search_embeddings(
        db=db,
        query=payload.query,
        top_k=payload.top_k,
        source_type=payload.source_type,
    )

    return [VectorSearchResult(**row) for row in results]
