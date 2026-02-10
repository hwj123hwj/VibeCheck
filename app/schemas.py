"""
Pydantic 响应/请求模型
"""
from pydantic import BaseModel
from typing import Optional


class SongBase(BaseModel):
    """歌曲基本信息"""
    id: str
    title: str
    artist: str
    album_cover: Optional[str] = None


class SongDetail(SongBase):
    """歌曲详情（含 AI 分析）"""
    lyrics: Optional[str] = None
    core_lyrics: Optional[str] = None
    review_text: Optional[str] = None
    vibe_tags: Optional[list[str]] = None
    vibe_scores: Optional[dict] = None
    recommend_scene: Optional[str] = None
    tfidf_vector: Optional[dict] = None

    class Config:
        from_attributes = True


class SongSearchResult(SongBase):
    """搜索结果中的单首歌曲"""
    review_text: Optional[str] = None
    vibe_tags: Optional[list[str]] = None
    core_lyrics: Optional[str] = None
    score: float = 0.0

    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str
    top_k: int = 10


class SearchResponse(BaseModel):
    """搜索响应"""
    query: str
    intent_type: str  # "vibe" | "lyrics" | "exact"
    results: list[SongSearchResult]


class RecommendResponse(BaseModel):
    """推荐响应"""
    source_song: SongBase
    recommendations: list[SongSearchResult]
