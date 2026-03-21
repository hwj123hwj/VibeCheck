"""
语义搜索接口
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import SearchResponse
from app.services.search import perform_hybrid_search

router = APIRouter()


@router.get("/search", response_model=SearchResponse)
async def search_songs(
    q: str = Query(..., min_length=1, max_length=200, description="自然语言搜索词"),
    top_k: int = Query(10, ge=1, le=50),
    mode: Optional[str] = Query(None, description="搜索模式: auto | vibe | lyrics | title | artist"),
    db: AsyncSession = Depends(get_db),
):
    """
    语义搜索歌曲

    mode=auto (默认): LLM 自动识别意图
    mode=vibe: 心情氛围，纯语义向量，跳过 LLM
    mode=lyrics: 搜歌词，歌词向量+关键词混合，跳过 LLM
    mode=title: 搜歌名，title ILIKE 直接匹配，最快
    mode=artist: 搜歌手，artist ILIKE 直接匹配，最快
    """
    return await perform_hybrid_search(q, top_k, db, mode=mode)
