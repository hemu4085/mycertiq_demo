# backend/app/scripts/generate_embeddings_openai.py

"""
Re-generate ALL embeddings for CME knowledge chunks.

This script:
- Deletes all existing embeddings for CME_EVENT
- Re-generates new embeddings for all 10,000 chunks
- Uses batch processing (64 chunks per batch)
- Stores embeddings in embedding_store with correct vector casting
"""

from typing import Any, Dict, List

from sqlalchemy import text
from sqlalchemy.orm import Session

from openai import OpenAI

from app.database import SessionLocal
from app.vector.manager import EMBEDDING_MODEL, get_openai_client

BATCH_SIZE = 64


def fetch_cme_chunks(db: Session, limit: int = BATCH_SIZE, offset: int = 0):
    """
    Returns a batch of CME chunks (source_type = 'cme_event')
    """
    sql = """
        SELECT
            id,
            source_type,
            source_id,
            raw_text
        FROM knowledge_chunk
        WHERE source_type = 'cme_event'
        ORDER BY id
        LIMIT :limit OFFSET :offset;
    """

    rows = db.execute(text(sql), {"limit": limit, "offset": offset}).mappings().all()
    return [dict(r) for r in rows]


def delete_old_embeddings(db: Session):
    """
    Delete all embeddings for CME_EVENT chunks.
    """
    sql = """
        DELETE FROM embedding_store
        WHERE source_type = 'cme_event';
    """
    db.execute(text(sql))
    db.commit()
    print("🧹 Deleted old embeddings where source_type = 'cme_event'.")


def embedding_to_literal(embedding: List[float]) -> str:
    """Convert list of floats to PostgreSQL vector literal string."""
    return "[" + ",".join(str(x) for x in embedding) + "]"


def insert_embeddings(db: Session, batch_rows: List[Dict[str, Any]], embeddings: List[List[float]]):
    """
    Insert batch embeddings into embedding_store
    """
    sql = """
        INSERT INTO embedding_store (
            knowledge_chunk_id,
            source_type,
            source_id,
            chunk_id,
            chunk_text,
            embedding,
            embedding_model
        )
        VALUES (
            :knowledge_chunk_id,
            :source_type,
            :source_id,
            :chunk_id,
            :chunk_text,
            (:embedding)::vector,
            :embedding_model
        );
    """

    for row, emb in zip(batch_rows, embeddings):
        embedding_literal = embedding_to_literal(emb)

        params = {
            "knowledge_chunk_id": row["id"],
            "source_type": row["source_type"],
            "source_id": row["source_id"],
            "chunk_id": str(row["id"]),
            "chunk_text": row["raw_text"],
            "embedding": embedding_literal,
            "embedding_model": EMBEDDING_MODEL,
        }

        db.execute(text(sql), params)

    db.commit()


def regenerate_all_embeddings():
    """
    Main pipeline:
    - Find total CME chunks
    - Delete old CME embeddings
    - Batch re-embed
    """
    client = get_openai_client()

    with SessionLocal() as db:
        # Count chunks
        total_sql = """
            SELECT COUNT(*) 
            FROM knowledge_chunk
            WHERE source_type = 'cme_event';
        """
        total_chunks = db.execute(text(total_sql)).scalar()
        print(f"📚 Total CME chunks to embed: {total_chunks}")

        # Delete old embeddings
        delete_old_embeddings(db)

        # Process in batches
        offset = 0
        inserted = 0

        while offset < total_chunks:
            batch = fetch_cme_chunks(db, limit=BATCH_SIZE, offset=offset)
            if not batch:
                break

            texts = [row["raw_text"] for row in batch]
            print(f"🔍 Embedding batch: offset {offset}, size {len(texts)}")

            # Call OpenAI embeddings
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts,
            )
            embeddings = [item.embedding for item in response.data]

            # Insert
            insert_embeddings(db, batch, embeddings)
            inserted += len(batch)

            print(f"✅ Inserted: {inserted}/{total_chunks}")

            offset += BATCH_SIZE

        print("🎉 Completed re-embedding of all CME chunks!")
        print(f"✨ Total embeddings inserted: {inserted}")


if __name__ == "__main__":
    print("🚀 Starting full CME re-embedding process...")
    regenerate_all_embeddings()
    print("🏁 All done!")
