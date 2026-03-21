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

    # cache key 不含 dedupe：始终缓存足量的原始候选列表，去重在返回前做 Python 过滤
    cache_key = (source.id, top_k, w_review, w_lyrics, w_tfidf)
    if cache_key not in _recommend_cache:
        src_review_vec = str(source.review_vector.tolist())
        src_lyrics_vec = str(source.lyrics_vector.tolist()) if source.lyrics_vector is not None else src_review_vec

        src_tfidf_keys: list[str] = []
        if source.tfidf_vector and isinstance(source.tfidf_vector, dict):
            src_tfidf_keys = list(source.tfidf_vector.keys())[:20]

        # 始终多取 5 倍候选，保证去重后仍有足够结果
        fetch_limit = top_k * 5

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

        db_result = await db.execute(recommend_sql, {
            "src_id": source.id,
            "src_review_vec": src_review_vec,
            "src_lyrics_vec": src_lyrics_vec,
            "src_tfidf_keys": src_tfidf_keys,
            "src_tfidf_len": len(src_tfidf_keys),
            "limit": fetch_limit,
            "w_review": w_review,
            "w_lyrics": w_lyrics,
            "w_tfidf": w_tfidf,
        })
        rows = db_result.fetchall()

        # 缓存原始全量候选列表（未去重）
        _recommend_cache[cache_key] = [
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

    # 从缓存取全量候选，按需去重后截取 top_k
    all_candidates = _recommend_cache[cache_key]
    if not dedupe:
        return all_candidates[:top_k]

    import re
    def _base_title(title: str) -> str:
        """提取主标题：去掉括号及其内容、版本后缀，用于模糊去重"""
        t = re.sub(r'[\(（\[【][^\)）\]】]*[\)）\]】]', '', title)  # 去括号内容
        t = re.sub(r'(cover|live|remix|dj|翻唱|版|ver\.?)\s*.*
, '', t, flags=re.IGNORECASE)
        return t.strip()

    seen_base_titles: set[str] = set()
    results = []
    for item in all_candidates:
        base = _base_title(item.title)
        if base in seen_base_titles:
            continue
        seen_base_titles.add(base)
        results.append(item)
        if len(results) >= top_k:
            break
    return results
