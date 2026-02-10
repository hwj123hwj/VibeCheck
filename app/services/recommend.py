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

    双向量余弦相似 + TF-IDF 关键词重叠
    """
    if source.review_vector is None:
        return []

    recommend_sql = sql_text("""
        SELECT
            id, title, artist, album_cover,
            vibe_tags, review_text, core_lyrics,
            (1 - (review_vector <=> CAST(:src_review_vec AS vector))) AS review_sim,
            COALESCE(1 - (lyrics_vector <=> CAST(:src_lyrics_vec AS vector)), 0) AS lyrics_sim
        FROM songs
        WHERE id != :src_id
          AND review_vector IS NOT NULL
          AND is_duplicate = false
        ORDER BY
            (1 - (review_vector <=> CAST(:src_review_vec AS vector))) * 0.5
            + COALESCE(1 - (lyrics_vector <=> CAST(:src_lyrics_vec AS vector)), 0) * 0.4
            DESC
        LIMIT :limit
    """)

    src_review_vec = str(list(source.review_vector)) if source.review_vector else None
    src_lyrics_vec = str(list(source.lyrics_vector)) if source.lyrics_vector else src_review_vec

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
            score=round(float(row.review_sim) * 0.5 + float(row.lyrics_sim) * 0.4, 4),
        )
        for row in rows
    ]
