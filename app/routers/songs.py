"""
歌曲相关接口
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db, Song
from app.schemas import SongDetail, SongBase

router = APIRouter()


@router.get("/songs/{song_id}", response_model=SongDetail)
async def get_song(song_id: str, db: Session = Depends(get_db)):
    """获取单首歌曲详情"""
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return song


@router.get("/songs/random/list", response_model=list[SongBase])
async def get_random_songs(count: int = 12, db: Session = Depends(get_db)):
    """随机获取歌曲（首页发现用）"""
    songs = (
        db.query(Song)
        .filter(
            Song.is_duplicate == False,
            Song.review_text != None,
        )
        .order_by(func.random())
        .limit(count)
        .all()
    )
    return songs
