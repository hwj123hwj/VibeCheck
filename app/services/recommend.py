"""
单曲推荐服务

基于已入库歌曲的向量，计算最相似的 Top-K 歌曲。

融合公式：
  FinalScore = 0.5 * Sim_review + 0.4 * Sim_lyrics + 0.1 * TF-IDF_overlap
"""
import re
from cachetools import TTLCache
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Song
from app.schemas import SongSearchResult

# 推荐缓存：最多 500 首，10 小时过期
_recommend_cache: TTLCache = TTLCache(maxsize=500, ttl=36000)

# 模糊去重用的正则：去掉括号内容、版本关键词、空格后内容，提取主标题
_BRACKET_RE = re.compile(r'[\(\uff08\[\u3010][^\)\uff09\]\u3011]*[\)\uff09\]\u3011]')
_VERSION_RE = re.compile('(cover|live|remix|dj|\u7ffb\u5531|\u7248|ver\\.?).*$', re.IGNORECASE)
_SPACE_RE   = re.compile(r'\s+.*$')


def _base_title(title: str) -> str:
    """提取主标题用于模糊去重"""
    t = _BRACKET_RE.sub('', title)   # 安和桥（DJ版）  -> 安和桥
    t = _VERSION_RE.sub('', t)       # 安和桥 Live     -> 安和桥
    t = _SPACE_RE.sub('', t)         # 老男孩 筷子兄弟  -> 老男孩
    return t.strip()


async def get_similar_songs(
    source: Song, top_k: int, db: AsyncSession,
    w_review: float = 0.5, w_lyrics: float = 0.4, w_tfidf: float = 0.1,
    dedupe: bool = False,
) -> list[SongSearchResult]:
    """
    给定一首歌，返回最相似的 Top-K 推荐

    双向量余弦相似 + TF-IDF 关键词重叠（参数化 SQL），权重可动态调整
    dedupe=True 时按主标题模糊去重，每个歌名只保留相似度最高的一条
    """
    if source.review_vector is None:
        return []

    # cache key 不含 dedupe：始终缓存足量原始候选列表，去重在返回前做 Python 过滤
    cache_key = (source.id, top_k, w_review, w_lyrics, w_tfidf)
    if cache_key not in _recommend_cache:
        src_review_vec = str(source.review_vector.tolist())
        src_lyrics_vec = (
            str(source.lyrics_vector.tolist())
            if source.lyrics_vector is not None
            else src_review_vec
        )

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

    all_candidates = _recommend_cache[cache_key]
    if not dedupe:
        return all_candidates[:top_k]

    # 把源歌曲自身的主标题预先加入 seen，避免推荐同名歌曲
    seen: set[str] = {_base_title(source.title)}
    results = []
    for item in all_candidates:
        base = _base_title(item.title)
        if base in seen:
            continue
        seen.add(base)
        results.append(item)
        if len(results) >= top_k:
            break
    return results
