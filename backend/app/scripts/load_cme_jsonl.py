import json
import pathlib
import psycopg2
from psycopg2.extras import execute_batch

# -----------------------------------------
# CONFIG
# -----------------------------------------

BASE_DIR = pathlib.Path(__file__).resolve().parents[2]
JSONL_PATH = BASE_DIR / "data" / "raw" / "cme_10000_rich.jsonl"

DB_HOST = "localhost"
DB_NAME = "mycertiq_demo"
DB_USER = "mycertiq_user"
DB_PASS = "mycertiq_dev"

BATCH_SIZE = 500


def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
    )


def load_cme():
    conn = get_conn()
    cur = conn.cursor()

    print(f"🔍 Reading JSONL CME dataset from: {JSONL_PATH}")
    rows = []
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))

    print(f"📦 Loaded {len(rows)} CME records")

    # -----------------------------------------
    # 1) Insert into cme_event (matches your schema)
    # -----------------------------------------
    print("📝 Inserting into cme_event...")

    cme_sql = """
        INSERT INTO cme_event (
            id,
            title,
            description,
            credit_type,
            credits,
            provider_name,
            format,
            audience,
            is_active
        )
        VALUES (
            %(id)s,
            %(title)s,
            %(description)s,
            %(credit_type)s,
            %(credits)s,
            %(provider)s,
            %(format)s,
            %(audience)s,
            TRUE
        );
    """

    execute_batch(cur, cme_sql, rows, page_size=BATCH_SIZE)
    conn.commit()
    print("✅ cme_event insert complete.")

    # -----------------------------------------
    # 2) Insert into knowledge_chunk (schema-aligned)
    # -----------------------------------------
    # Your knowledge_chunk schema (from DDL):
    #   id bigserial PK
    #   source_type varchar(50) NOT NULL
    #   source_id bigint
    #   section varchar(255)
    #   raw_text text NOT NULL
    #   semantic_document_id bigint
    #   created_at timestamptz DEFAULT now()
    #
    # We will:
    #   - let id auto-increment
    #   - source_type = 'cme_event'
    #   - source_id = CME id
    #   - section = 'full'
    #   - raw_text = title + "\n\n" + description
    #   - semantic_document_id = NULL
    # -----------------------------------------

    print("🧠 Inserting knowledge chunks...")

    kc_rows = []
    for r in rows:
        kc_rows.append({
            "source_type": "cme_event",
            "source_id": r["id"],
            "section": "full",
            "raw_text": r["title"] + "\n\n" + r["description"],
        })

    kc_sql = """
        INSERT INTO knowledge_chunk (
            source_type,
            source_id,
            section,
            raw_text
        )
        VALUES (
            %(source_type)s,
            %(source_id)s,
            %(section)s,
            %(raw_text)s
        );
    """

    execute_batch(cur, kc_sql, kc_rows, page_size=BATCH_SIZE)
    conn.commit()
    print("✅ knowledge_chunk insert complete.")

    # -----------------------------------------
    # 3) NOTE: We are *not* populating embedding_store here.
    #
    # A separate script will:
    #   - read knowledge_chunk rows
    #   - generate embeddings via your chosen model
    #   - insert into embedding_store with correct columns
    # -----------------------------------------

    cur.close()
    conn.close()
    print("🎉 DONE! CME data + knowledge chunks loaded successfully.")


if __name__ == "__main__":
    load_cme()
