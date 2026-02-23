-- ============================================================
-- HNSW 向量索引 — 将 5.3w+ 规模的 <=> 全表扫描加速至 100ms 级
-- 
-- 前置条件: pgvector >= 0.5.0
-- 执行方式: psql -U root -d music_db -f 001_create_hnsw_indexes.sql
-- 预计耗时: 约 3~10 分钟（取决于数据规模和硬件）
-- ============================================================

-- 1. 评语向量 HNSW 索引（搜索与推荐均使用）
CREATE INDEX IF NOT EXISTS idx_review_vector_hnsw
  ON songs USING hnsw (review_vector vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- 2. 精华歌词向量 HNSW 索引
CREATE INDEX IF NOT EXISTS idx_lyrics_vector_hnsw
  ON songs USING hnsw (lyrics_vector vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- 3. 设置运行时搜索参数 (可选，提升召回精度)
-- 在应用层或 session 级别设置:
-- SET hnsw.ef_search = 40;

-- 验证索引是否创建成功
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'songs'
  AND indexname LIKE '%hnsw%';
