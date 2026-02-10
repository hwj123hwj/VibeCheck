"""
语义搜索接口

将 deploy_crawler/hybrid_search_test.py 的逻辑正式化。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import SearchResponse
from app.services.search import perform_hybrid_search

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search_songs(
    q: str = Query(..., min_length=1, max_length=200, description="自然语言搜索词"),
    top_k: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """
    语义搜索歌曲

    支持：
    - 情感/场景描述: "下雨天适合听的伤感歌"
    - 歌词片段: "后来我总算学会了如何去爱"
    - 精确搜索: "周杰伦 晴天"
    """
    return await perform_hybrid_search(q, top_k, db)
