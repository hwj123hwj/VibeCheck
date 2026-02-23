"""
执行 HNSW 向量索引迁移

在 5.3w+ 规模数据上创建 HNSW 索引，将向量检索从全表扫描加速至 100ms 级。
"""
import time
import sqlalchemy

DB_URL = "postgresql://root:15671040800q@49.233.41.129:5433/music_db"

engine = sqlalchemy.create_engine(DB_URL)

with engine.connect() as conn:
    # ── Pre-flight checks ──
    r = conn.execute(sqlalchemy.text(
        "SELECT extversion FROM pg_extension WHERE extname='vector'"
    ))
    row = r.fetchone()
    print(f"[CHECK] pgvector version: {row[0] if row else 'NOT INSTALLED'}")

    r2 = conn.execute(sqlalchemy.text(
        "SELECT indexname FROM pg_indexes WHERE tablename='songs' AND indexname LIKE '%hnsw%'"
    ))
    existing = [row[0] for row in r2.fetchall()]
    print(f"[CHECK] Existing HNSW indexes: {existing}")

    r3 = conn.execute(sqlalchemy.text("SELECT count(*) FROM songs WHERE review_vector IS NOT NULL"))
    print(f"[CHECK] Rows with review_vector: {r3.fetchone()[0]}")

    r4 = conn.execute(sqlalchemy.text("SELECT count(*) FROM songs WHERE lyrics_vector IS NOT NULL"))
    print(f"[CHECK] Rows with lyrics_vector: {r4.fetchone()[0]}")

    # ── Create HNSW indexes ──
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

    # ── Verify ──
    r5 = conn.execute(sqlalchemy.text(
        "SELECT indexname, pg_size_pretty(pg_relation_size(indexname::regclass)) as size "
        "FROM pg_indexes WHERE tablename='songs' AND indexname LIKE '%hnsw%'"
    ))
    print("\n[RESULT] HNSW Indexes:")
    for row in r5.fetchall():
        print(f"  - {row[0]}  ({row[1]})")

    print("\n✅ Migration complete!")
