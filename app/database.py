"""
数据库连接 & ORM 模型定义

这是 VibeCheck 后端 API 使用的数据库层。
Song 模型与 deploy_crawler/db_init.py 保持字段完全一致。
"""
from sqlalchemy import create_engine, Column, String, Text, DateTime, Boolean, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from typing import Generator

from app.config import get_settings

# ---------- Engine & Session ----------

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入：获取数据库 Session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- ORM Model ----------

class Song(Base):
    """
    歌曲表 — 与 deploy_crawler/db_init.py 中的定义保持一致。
    任何字段变更需要同步到 deploy_crawler 侧。
    """
    __tablename__ = "songs"

    id = Column(String(50), primary_key=True, comment="网易云音乐歌曲ID")
    title = Column(String(255), nullable=False, comment="歌曲标题")
    artist = Column(String(255), nullable=False, comment="歌手")
    lyrics = Column(Text, comment="原始歌词")
    segmented_lyrics = Column(Text, comment="分词后的歌词 (用于 TF-IDF)")
    review_text = Column(Text, comment="LLM 生成的情感评语")
    vibe_tags = Column(JSONB, comment="LLM 提取的氛围标签 (JSONB 数组)")
    vibe_scores = Column(JSONB, comment="情感维度评分 (JSONB)")
    recommend_scene = Column(Text, comment="LLM 建议的听歌场景")

    # 核心向量字段 (BAAI/bge-m3 = 1024 维)
    review_vector = Column(Vector(1024), comment="评语 Embedding 向量")
    core_lyrics = Column(Text, comment="AI或算法提取的精华歌词/副歌")
    lyrics_vector = Column(Vector(1024), comment="精华歌词的语义向量索引")

    # TF-IDF (JSONB 存储 Top-N 关键词 + 权重)
    tfidf_vector = Column(JSONB, comment="TF-IDF 关键词 (JSON)")

    album_cover = Column(String(500), nullable=True, comment="专辑封面 URL")
    is_duplicate = Column(Boolean, default=False, comment="是否为重复歌曲")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="最后更新时间")
