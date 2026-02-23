"""Run HNSW index migration using DATABASE_URL from environment."""
import os
import time

import sqlalchemy

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = os.getenv("DB_PORT", "5433")
    DB_NAME = os.getenv("DB_NAME", "music_db")
    DB_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = sqlalchemy.create_engine(DB_URL)

with engine.connect() as conn:
    r = conn.execute(sqlalchemy.text("SELECT extversion FROM pg_extension WHERE extname='vector'"))
    row = r.fetchone()
    print(f"[CHECK] pgvector version: {row[0] if row else 'NOT INSTALLED'}")

    r2 = conn.execute(sqlalchemy.text("SELECT indexname FROM pg_indexes WHERE tablename='songs' AND indexname LIKE '%hnsw%'"))
    existing = [row[0] for row in r2.fetchall()]
    print(f"[CHECK] Existing HNSW indexes: {existing}")

    r3 = conn.execute(sqlalchemy.text("SELECT count(*) FROM songs WHERE review_vector IS NOT NULL"))
    print(f"[CHECK] Rows with review_vector: {r3.fetchone()[0]}")

    r4 = conn.execute(sqlalchemy.text("SELECT count(*) FROM songs WHERE lyrics_vector IS NOT NULL"))
    print(f"[CHECK] Rows with lyrics_vector: {r4.fetchone()[0]}")

    if "idx_review_vector_hnsw" not in existing:
        print("\n[MIGRATE] Creating idx_review_vector_hnsw ... (this may take a few minutes)")
        t0 = time.time()
        conn.execute(sqlalchemy.text(
            "CREATE INDEX IF NOT EXISTS idx_review_vector_hnsw "
            "ON songs USING hnsw (review_vector vector_cosine_ops) "
            "WITH (m = 16, ef_construction = 64)"
        ))
        conn.commit()
        print(f"[MIGRATE] idx_review_vector_hnsw created in {time.time() - t0:.1f}s")
    else:
        print("\n[SKIP] idx_review_vector_hnsw already exists")

    if "idx_lyrics_vector_hnsw" not in existing:
        print("[MIGRATE] Creating idx_lyrics_vector_hnsw ... (this may take a few minutes)")
        t0 = time.time()
        conn.execute(sqlalchemy.text(
            "CREATE INDEX IF NOT EXISTS idx_lyrics_vector_hnsw "
            "ON songs USING hnsw (lyrics_vector vector_cosine_ops) "
            "WITH (m = 16, ef_construction = 64)"
        ))
        conn.commit()
        print(f"[MIGRATE] idx_lyrics_vector_hnsw created in {time.time() - t0:.1f}s")
    else:
        print("[SKIP] idx_lyrics_vector_hnsw already exists")

    r5 = conn.execute(sqlalchemy.text(
        "SELECT indexname, pg_size_pretty(pg_relation_size(indexname::regclass)) as size "
        "FROM pg_indexes WHERE tablename='songs' AND indexname LIKE '%hnsw%'"
    ))
    print("\n[RESULT] HNSW Indexes:")
    for row in r5.fetchall():
        print(f"  - {row[0]}  ({row[1]})")

    print("\nMigration complete!")
