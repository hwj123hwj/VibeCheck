"""
单曲推荐服务

基于已入库歌曲的向量，计算最相似的 Top-K 歌曲。

融合公式：
  FinalScore = 0.5 * Sim_review + 0.4 * Sim_lyrics + 0.1 * TF-IDF_overlap
"""
from sqlalchemy import text as sql_text
from sqlalchemy.orm import Session

from app.database import Song
from app.schemas import SongSearchResult


async def get_similar_songs(
    source: Song, top_k: int, db: Session
) -> list[SongSearchResult]:
    """
    给定一首歌，返回最相似的 Top-K 推荐

    双向量余弦相似 + TF-IDF 关键词重叠（JSONB key 交集）
    """
    if source.review_vector is None:
        return []

    # pgvector 返回 numpy 数组，.tolist() 转为 Python 原生 float 列表
    src_review_vec = str(source.review_vector.tolist())
    src_lyrics_vec = str(source.lyrics_vector.tolist()) if source.lyrics_vector is not None else src_review_vec

    # 提取源歌曲的 TF-IDF 关键词集合，用于计算关键词重叠
    src_tfidf_keys: list[str] = []
    if source.tfidf_vector and isinstance(source.tfidf_vector, dict):
        src_tfidf_keys = list(source.tfidf_vector.keys())

    # 构建 TF-IDF 重叠计算的 SQL 片段
    # 使用 jsonb '?' 操作符统计目标歌曲 tfidf_vector 中命中源歌曲关键词的数量
    if src_tfidf_keys:
        # 每命中一个关键词 +1，最终除以源关键词总数得到 0~1 的重叠比例
        overlap_parts = " + ".join(
            f"CASE WHEN tfidf_vector ? '{kw}' THEN 1 ELSE 0 END"
            for kw in src_tfidf_keys[:20]  # 取 Top-20 关键词防止 SQL 过长
        )
        tfidf_overlap_expr = f"({overlap_parts})::float / {len(src_tfidf_keys[:20])}"
    else:
        tfidf_overlap_expr = "0"

    recommend_sql = sql_text(f"""
        SELECT
            id, title, artist, album_cover,
            vibe_tags, review_text, core_lyrics,
            (1 - (review_vector <=> CAST(:src_review_vec AS vector))) AS review_sim,
            COALESCE(1 - (lyrics_vector <=> CAST(:src_lyrics_vec AS vector)), 0) AS lyrics_sim,
            {tfidf_overlap_expr} AS tfidf_overlap
        FROM songs
        WHERE id != :src_id
          AND review_vector IS NOT NULL
          AND is_duplicate = false
        ORDER BY
            (1 - (review_vector <=> CAST(:src_review_vec AS vector))) * 0.5
            + COALESCE(1 - (lyrics_vector <=> CAST(:src_lyrics_vec AS vector)), 0) * 0.4
            + {tfidf_overlap_expr} * 0.1
            DESC
        LIMIT :limit
    """)

    rows = db.execute(recommend_sql, {
        "src_id": source.id,
        "src_review_vec": src_review_vec,
        "src_lyrics_vec": src_lyrics_vec,
        "limit": top_k,
    }).fetchall()

    return [
        SongSearchResult(
            id=row.id,
            title=row.title,
            artist=row.artist,
            album_cover=row.album_cover,
            review_text=row.review_text,
            vibe_tags=row.vibe_tags,
            core_lyrics=row.core_lyrics,
            score=round(
                float(row.review_sim) * 0.5
                + float(row.lyrics_sim) * 0.4
                + float(row.tfidf_overlap) * 0.1,
                4,
            ),
        )
        for row in rows
    ]
