"""
混合搜索服务

将 deploy_crawler/hybrid_search_test.py 中验证过的混合检索逻辑
封装为可复用的服务函数。

三路融合:
  1. review_vector  — 评语语义相似度
  2. lyrics_vector  — 精华歌词语义相似度
  3. rational_score — TF-IDF 关键词 + 精确匹配
"""
import jieba
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.schemas import SearchResponse, SongSearchResult
from app.services.embedding import get_embedding
from app.services.llm import parse_search_intent
from app.config import get_settings

settings = get_settings()

# 停用词 (搜索时过滤)
ULTRA_STOP_WORDS = {
    "想听", "给我", "推荐", "一首", "有些", "听听", "有关", "关于",
    "那些", "的", "了", "在", "我", "你", "他", "她", "歌", "适合",
    "那种", "一种", "，", "。", "！", "？", " ",
}


def _clean_query_words(query: str) -> list[str]:
    """分词并过滤停用词"""
    words = jieba.lcut(query)
    cleaned = [w for w in words if w not in ULTRA_STOP_WORDS and len(w.strip()) > 1]
    return cleaned if cleaned else words


# 权重配置（从 config 读取，支持环境变量覆盖）
WEIGHT_MAP = {
    "lyrics": settings.SEARCH_WEIGHT_LYRICS,
    "exact":  settings.SEARCH_WEIGHT_EXACT,
    "vibe":   settings.SEARCH_WEIGHT_VIBE,
}


async def perform_hybrid_search(
    user_query: str, top_k: int, db: Session
) -> SearchResponse:
    """执行混合搜索并返回结构化结果"""

    # 1. AI 意图路由
    intent = parse_search_intent(user_query)
    intent_type = intent.get("type", "vibe")
    weights = WEIGHT_MAP.get(intent_type, WEIGHT_MAP["vibe"])

    # 2. 向量化用户查询 (异步)
    vibe_query = intent.get("vibe") or user_query
    query_vec = await get_embedding(vibe_query)

    # 3. 关键词分词
    cleaned_words = _clean_query_words(user_query)
    ts_query = " | ".join(cleaned_words)

    # 4. 混合 SQL (双向量 + TF-IDF + 精确匹配)
    search_sql = sql_text("""
        WITH scoring_pool AS (
            SELECT
                id, title, artist, album_cover,
                vibe_tags, review_text, core_lyrics,
                (1 - (review_vector <=> CAST(:q_vec AS vector))) AS review_score,
                COALESCE(1 - (lyrics_vector <=> CAST(:q_vec AS vector)), 0) AS lyrics_score,
                (
                    CASE WHEN artist ILIKE :artist_q THEN 4.0 ELSE 0 END +
                    CASE WHEN title ILIKE :title_q THEN 3.0 ELSE 0 END +
                    ts_rank_cd(
                        to_tsvector('simple', title || ' ' || artist || ' ' || COALESCE(segmented_lyrics, '')),
                        to_tsquery('simple', :ts_q)
                    )
                ) AS rational_score
            FROM songs
            WHERE review_vector IS NOT NULL
              AND is_duplicate = false
        )
        SELECT *,
               (review_score * :w_rev
                + lyrics_score * :w_lyr
                + LEAST(rational_score, 4.0) / 4.0 * :w_rat
               ) AS final_score
        FROM scoring_pool
        WHERE review_score > :threshold OR lyrics_score > :threshold
        ORDER BY final_score DESC
        LIMIT :limit
    """)

    rows = db.execute(search_sql, {
        "q_vec": str(query_vec),
        "ts_q": ts_query,
        "artist_q": f"%{intent['artist']}%" if intent.get("artist") else "%__NONE__%",
        "title_q": f"%{intent['title']}%" if intent.get("title") else "%__NONE__%",
        "w_rev": weights["review"],
        "w_lyr": weights["lyrics"],
        "w_rat": weights["rational"],
        "threshold": settings.SEARCH_SCORE_THRESHOLD,
        "limit": top_k,
    }).fetchall()

    # 5. 组装响应（含可解释性子分数）
    results = [
        SongSearchResult(
            id=row.id,
            title=row.title,
            artist=row.artist,
            album_cover=row.album_cover,
            review_text=row.review_text,
            vibe_tags=row.vibe_tags,
            core_lyrics=row.core_lyrics,
            score=round(float(row.final_score), 4),
            review_score=round(float(row.review_score), 4),
            lyrics_score=round(float(row.lyrics_score), 4),
            rational_score=round(float(row.rational_score), 4),
        )
        for row in rows
    ]

    return SearchResponse(
        query=user_query,
        intent_type=intent_type,
        results=results,
    )
