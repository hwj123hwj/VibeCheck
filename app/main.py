"""
FastAPI 应用入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import search, recommend, songs

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="基于 LLM 语义评语与 TF-IDF 的混合音乐推荐系统 API",
    version="0.1.0",
)

# CORS 跨域配置 (允许前端访问)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(songs.router, prefix="/api", tags=["Songs"])
app.include_router(search.router, prefix="/api", tags=["Search"])
app.include_router(recommend.router, prefix="/api", tags=["Recommend"])


@app.get("/")
async def root():
    return {"message": "VibeCheck API is running", "docs": "/docs"}
