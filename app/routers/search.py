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
    mode: Optional[str] = Query(None, description="搜索模式: auto | vibe | exact"),
    db: AsyncSession = Depends(get_db),
):
    """
    语义搜索歌曲

    mode=auto (默认): LLM 自动识别意图
    mode=vibe: 直接走氛围语义搜索，跳过 LLM
    mode=exact: 直接走精确关键词匹配，跳过 LLM 和 Embedding
    """
    return await perform_hybrid_search(q, top_k, db, mode=mode)
