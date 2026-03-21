"""
混合搜索服务

将 deploy_crawler/hybrid_search_test.py 中验证过的混合检索逻辑
封装为可复用的服务函数。

三路融合:
  1. review_vector  — 评语语义相似度
  2. lyrics_vector  — 精华歌词语义相似度
  3. rational_score — TF-IDF 关键词 + 精确匹配
"""
import asyncio
import jieba
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

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


async def _exact_search(
    intent: dict, top_k: int, db: AsyncSession
) -> list[SongSearchResult]:
    """exact 类型：直接走精确 SQL，不做向量计算"""
    exact_sql = sql_text("""
        SELECT
            id, title, artist, album_cover,
            vibe_tags, review_text, core_lyrics,
            (
                CASE WHEN artist ILIKE :artist_q THEN 2.0 ELSE 0 END +
                CASE WHEN title  ILIKE :title_q  THEN 3.0 ELSE 0 END
            ) AS score
        FROM songs
        WHERE is_duplicate = false
          AND (
              (:has_artist AND artist ILIKE :artist_q) OR
              (:has_title  AND title  ILIKE :title_q)
          )
        ORDER BY score DESC
        LIMIT :limit
    """)
    artist_q = f"%{intent['artist']}%" if intent.get("artist") else "%%"
    title_q  = f"%{intent['title']}%"  if intent.get("title")  else "%%"
    result = await db.execute(exact_sql, {
        "artist_q":   artist_q,
        "title_q":    title_q,
        "has_artist": bool(intent.get("artist")),
        "has_title":  bool(intent.get("title")),
        "limit":      top_k,
    })
    rows = result.fetchall()
    return [
        SongSearchResult(
            id=row.id, title=row.title, artist=row.artist,
            album_cover=row.album_cover, review_text=row.review_text,
            vibe_tags=row.vibe_tags, core_lyrics=row.core_lyrics,
            score=round(float(row.score) / 5.0, 4),  # 归一化到 0~1（最高分 artist+title = 5.0）
        )
        for row in rows
    ]


async def perform_hybrid_search(
    user_query: str, top_k: int, db: AsyncSession,
    mode: str | None = None,
) -> SearchResponse:
    """执行混合搜索并返回结构化结果

    mode=None/auto : LLM 自动识别意图（默认）
    mode=vibe      : 直接走氛围语义，跳过 LLM
    mode=exact     : 直接走精确关键词匹配，跳过 LLM 和 Embedding
    """

    # ── 手动指定 exact 模式：分词后走关键词 SQL，跳过 LLM 和 Embedding ──
    if mode == "exact":
        cleaned_words = _clean_query_words(user_query)
        ts_query = " | ".join(cleaned_words)
        # 把每个分词结果都作为 ILIKE 模糊匹配候选
        like_pattern = "%" + "%".join(cleaned_words) + "%"
        exact_kw_sql = sql_text("""
            SELECT
                id, title, artist, album_cover,
                vibe_tags, review_text, core_lyrics,
                (
                    CASE WHEN artist ILIKE :like_q THEN 2.0 ELSE 0 END +
                    CASE WHEN title  ILIKE :like_q THEN 3.0 ELSE 0 END +
                    ts_rank_cd(
                        to_tsvector('simple', title || ' ' || artist || ' ' || COALESCE(segmented_lyrics, '')),
                        to_tsquery('simple', :ts_q)
                    )
                ) AS score
            FROM songs
            WHERE is_duplicate = false
              AND (
                  artist ILIKE :like_q OR
                  title  ILIKE :like_q OR
                  to_tsvector('simple', title || ' ' || artist || ' ' || COALESCE(segmented_lyrics, ''))
                      @@ to_tsquery('simple', :ts_q)
              )
            ORDER BY score DESC
            LIMIT :limit
        """)
        result = await db.execute(exact_kw_sql, {
            "like_q": f"%{user_query}%",
            "ts_q": ts_query,
            "limit": top_k,
        })
        rows = result.fetchall()
        results = [
            SongSearchResult(
                id=row.id, title=row.title, artist=row.artist,
                album_cover=row.album_cover, review_text=row.review_text,
                vibe_tags=row.vibe_tags, core_lyrics=row.core_lyrics,
                score=round(min(float(row.score) / 5.0, 1.0), 4),
            )
            for row in rows
        ]
        return SearchResponse(query=user_query, intent_type="exact", results=results)

    # ── 手动指定 vibe 模式：跳过 LLM，直接氛围语义搜索 ──
    if mode == "vibe":
        query_vec = await get_embedding(user_query)
        intent_type = "vibe"
        weights = WEIGHT_MAP["vibe"]
        intent = {}

    # ── 手动指定 lyrics 模式：跳过 LLM，歌词向量 + 关键词混合 ──
    elif mode == "lyrics":
        query_vec = await get_embedding(user_query)
        intent_type = "lyrics"
        weights = WEIGHT_MAP["lyrics"]
        intent = {}

    else:
        # ── 自动模式：LLM 意图解析 与 Embedding 向量化 并发执行 ──
        intent, query_vec = await asyncio.gather(
            parse_search_intent(user_query),
            get_embedding(user_query),
        )

        intent_type = intent.get("type", "vibe")
        weights = WEIGHT_MAP.get(intent_type, WEIGHT_MAP["vibe"])

        # exact 类型：有明确歌手或歌名，直接精确匹配，跳过向量计算
        if intent_type == "exact" and (intent.get("artist") or intent.get("title")):
            results = await _exact_search(intent, top_k, db)
            # 精确匹配无结果时降级为混合搜索
            if results:
                return SearchResponse(query=user_query, intent_type=intent_type, results=results)

        # 若 LLM 提取的 vibe 与原始 query 不同，则单独向量化 vibe
        vibe_query = intent.get("vibe") or user_query
        if vibe_query != user_query:
            query_vec = await get_embedding(vibe_query)

    # 2. 关键词分词
    cleaned_words = _clean_query_words(user_query)
    ts_query = " | ".join(cleaned_words)

    # 3. 混合 SQL (双向量 + TF-IDF + 精确匹配)
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

    result = await db.execute(search_sql, {
        "q_vec": str(query_vec),
        "ts_q": ts_query,
        "artist_q": f"%{intent['artist']}%" if intent.get("artist") else "%__NONE__%",
        "title_q": f"%{intent['title']}%" if intent.get("title") else "%__NONE__%",
        "w_rev": weights["review"],
        "w_lyr": weights["lyrics"],
        "w_rat": weights["rational"],
        "threshold": settings.SEARCH_SCORE_THRESHOLD,
        "limit": top_k,
    })
    rows = result.fetchall()

    # 4. 组装响应（含可解释性子分数）
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
