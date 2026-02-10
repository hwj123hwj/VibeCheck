"""
推荐接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db, Song
from app.schemas import RecommendResponse, SongBase
from app.services.recommend import get_similar_songs

router = APIRouter()


@router.get("/recommend/{song_id}", response_model=RecommendResponse)
async def recommend_songs(
    song_id: str,
    top_k: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    基于单首歌曲推荐相似歌曲

    混合融合：review_vector + lyrics_vector + tfidf 关键词
    """
    source = db.query(Song).filter(Song.id == song_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Song not found")

    recommendations = await get_similar_songs(source, top_k, db)

    return RecommendResponse(
        source_song=SongBase(
            id=source.id,
            title=source.title,
            artist=source.artist,
            album_cover=source.album_cover,
        ),
        recommendations=recommendations,
    )
