# backend/app/vector/manager.py

from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session
from openai import OpenAI

# Use the 1536-dimensional model to match your existing DB embeddings
EMBEDDING_MODEL = "text-embedding-3-small"

_client: Optional[OpenAI] = None


def get_openai_client() -> OpenAI:
    """
    Lazy initialize OpenAI client.
    """
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def get_query_embedding(query: str) -> List[float]:
    """
    Generate embedding vector for user query string using OpenAI.
    """
    client = get_openai_client()
    response = client.embeddings.create(
        input=query,
        model=EMBEDDING_MODEL,
    )

    return response.data[0].embedding


def search_embeddings(
    db: Session,
    query: str,
    top_k: int = 5,
    source_type: Optional[str] = None,
    embedding_model: str = EMBEDDING_MODEL,
) -> List[Dict[str, Any]]:
    """
    Perform vector search over embedding_store using pgvector cosine distance.
    """

    # 1) Generate embedding list of floats
    embedding_list = get_query_embedding(query)

    # 2) Convert list to PostgreSQL vector literal
    embedding_literal = "[" + ",".join(str(x) for x in embedding_list) + "]"

    # 3) Build SQL (note use of (:embedding)::vector)
    base_sql = """
        SELECT
            id,
            knowledge_chunk_id,
            source_type,
            source_id,
            chunk_id,
            chunk_text,
            embedding_model,
            1.0 - (embedding <=> (:embedding)::vector) AS score
        FROM embedding_store
        WHERE embedding_model = :embedding_model
    """

    if source_type:
        base_sql += " AND source_type = :source_type\n"

    base_sql += """
        ORDER BY embedding <=> (:embedding)::vector
        LIMIT :top_k;
    """

    # 4) SQL parameters
    params: Dict[str, Any] = {
        "embedding": embedding_literal,
        "embedding_model": embedding_model,
        "top_k": top_k,
    }

    if source_type:
        params["source_type"] = source_type

    # 5) Run search
    result = db.execute(text(base_sql), params).mappings().all()
    return [dict(row) for row in result]
