"""
应用配置 - 从环境变量加载所有配置项
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置，所有值优先从 .env / 环境变量读取"""

    # --- 数据库 ---
    DB_USER: str = "root"
    DB_PASSWORD: str = "15671040800q"
    DB_HOST: str = "127.0.0.1"
    DB_PORT: str = "5433"
    DB_NAME: str = "music_db"

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # --- 硅基流动 Embedding ---
    GUIJI_API_KEY: str = ""
    GUIJI_EMB_URL: str = "https://api.siliconflow.cn/v1/embeddings"
    GUIJI_EMB_MODEL: str = "BAAI/bge-m3"

    # --- LongMao LLM ---
    LONGMAO_API_KEY: str = ""
    LONGMAO_BASE_URL: str = "https://api.longcat.chat/openai"
    LONGMAO_MODEL: str = "LongCat-Flash-Chat"

    # --- 应用 ---
    APP_NAME: str = "VibeCheck"
    DEBUG: bool = False
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # --- 搜索参数 ---
    SEARCH_SCORE_THRESHOLD: float = 0.4  # 向量相似度最低阈值
    SEARCH_WEIGHT_VIBE: dict = {"review": 0.6, "lyrics": 0.2, "rational": 0.2}
    SEARCH_WEIGHT_LYRICS: dict = {"review": 0.2, "lyrics": 0.6, "rational": 0.2}
    SEARCH_WEIGHT_EXACT: dict = {"review": 0.1, "lyrics": 0.1, "rational": 0.8}

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """单例模式获取配置"""
    return Settings()
