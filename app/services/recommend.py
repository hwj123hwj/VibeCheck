"""
单曲推荐服务

基于已入库歌曲的向量，计算最相似的 Top-K 歌曲。

融合公式：
  FinalScore = 0.5 * Sim_review + 0.4 * Sim_lyrics + 0.1 * TF-IDF_overlap
"""
from cachetools import TTLCache
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Song
from app.schemas import SongSearchResult

# 推荐缓存：最多 500 首，1 小时过期
_recommend_cache: TTLCache = TTLCache(maxsize=500, ttl=3600)


async def get_similar_songs(
    source: Song, top_k: int, db: AsyncSession,
    w_review: float = 0.5, w_lyrics: float = 0.4, w_tfidf: float = 0.1,
    dedupe: bool = False,
) -> list[SongSearchResult]:
    """
    给定一首歌，返回最相似的 Top-K 推荐

    双向量余弦相似 + TF-IDF 关键词重叠（参数化 SQL），权重可动态调整
    dedupe=True 时按歌名去重，每个歌名只保留相似度最高的一条
    """
    if source.review_vector is None:
        return []

    cache_key = (source.id, top_k, w_review, w_lyrics, w_tfidf, dedupe)
    if cache_key in _recommend_cache:
        return _recommend_cache[cache_key]

    src_review_vec = str(source.review_vector.tolist())
    src_lyrics_vec = str(source.lyrics_vector.tolist()) if source.lyrics_vector is not None else src_review_vec

    src_tfidf_keys: list[str] = []
    if source.tfidf_vector and isinstance(source.tfidf_vector, dict):
        src_tfidf_keys = list(source.tfidf_vector.keys())[:20]

    # dedupe=True 时用 DISTINCT ON 按歌名去重（先算分，再按 title 取最高分那条）
    # 必须套一层子查询，因为 DISTINCT ON 要求排序字段以去重列开头
    if dedupe:
        recommend_sql = sql_text("""
            WITH candidates AS (
                SELECT
                    id, title, artist, album_cover,
                    vibe_tags, review_text, core_lyrics,
                    (1 - (review_vector <=> CAST(:src_review_vec AS vector))) AS review_sim,
                    COALESCE(1 - (lyrics_vector <=> CAST(:src_lyrics_vec AS vector)), 0) AS lyrics_sim,
                    COALESCE(
                        (
                            SELECT COUNT(*)::float
                            FROM jsonb_object_keys(COALESCE(tfidf_vector, '{}'::jsonb)) AS k(key)
                            WHERE k.key = ANY(CAST(:src_tfidf_keys AS text[]))
                        ) / NULLIF(:src_tfidf_len, 0),
                        0
                    ) AS tfidf_overlap,
                    review_sim * :w_review
                        + lyrics_sim * :w_lyrics
                        + tfidf_overlap * :w_tfidf AS final_score
                FROM songs
                WHERE id != :src_id
                  AND review_vector IS NOT NULL
                  AND is_duplicate = false
            ),
            deduped AS (
                SELECT DISTINCT ON (title)
                    id, title, artist, album_cover,
                    vibe_tags, review_text, core_lyrics,
                    review_sim, lyrics_sim, tfidf_overlap, final_score
                FROM candidates
                ORDER BY title, final_score DESC
            )
            SELECT * FROM deduped
            ORDER BY final_score DESC
            LIMIT :limit
        """)
    else:
        recommend_sql = sql_text("""
            WITH candidates AS (
                SELECT
                    id, title, artist, album_cover,
                    vibe_tags, review_text, core_lyrics,
                    (1 - (review_vector <=> CAST(:src_review_vec AS vector))) AS review_sim,
                    COALESCE(1 - (lyrics_vector <=> CAST(:src_lyrics_vec AS vector)), 0) AS lyrics_sim,
                    COALESCE(
                        (
                            SELECT COUNT(*)::float
                            FROM jsonb_object_keys(COALESCE(tfidf_vector, '{}'::jsonb)) AS k(key)
                            WHERE k.key = ANY(CAST(:src_tfidf_keys AS text[]))
                        ) / NULLIF(:src_tfidf_len, 0),
                        0
                    ) AS tfidf_overlap
                FROM songs
                WHERE id != :src_id
                  AND review_vector IS NOT NULL
                  AND is_duplicate = false
            )
            SELECT
                id, title, artist, album_cover,
                vibe_tags, review_text, core_lyrics,
                review_sim, lyrics_sim, tfidf_overlap
            FROM candidates
            ORDER BY
                review_sim * :w_review
                + lyrics_sim * :w_lyrics
                + tfidf_overlap * :w_tfidf
                DESC
            LIMIT :limit
        """)

    result = await db.execute(recommend_sql, {
        "src_id": source.id,
        "src_review_vec": src_review_vec,
        "src_lyrics_vec": src_lyrics_vec,
        "src_tfidf_keys": src_tfidf_keys,
        "src_tfidf_len": len(src_tfidf_keys),
        "limit": top_k,
        "w_review": w_review,
        "w_lyrics": w_lyrics,
        "w_tfidf": w_tfidf,
    })
    rows = result.fetchall()

    results = [
        SongSearchResult(
            id=row.id,
            title=row.title,
            artist=row.artist,
            album_cover=row.album_cover,
            review_text=row.review_text,
            vibe_tags=row.vibe_tags,
            core_lyrics=row.core_lyrics,
            score=round(
                float(row.review_sim) * w_review
                + float(row.lyrics_sim) * w_lyrics
                + float(row.tfidf_overlap) * w_tfidf,
                4,
            ),
        )
        for row in rows
    ]
    _recommend_cache[cache_key] = results
    return results
