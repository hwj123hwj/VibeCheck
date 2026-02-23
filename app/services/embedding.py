"""
Embedding 服务 - 调用硅基流动 BAAI/bge-m3

封装向量化调用逻辑，供搜索和推荐服务使用。
使用 httpx.AsyncClient 避免阻塞 FastAPI 事件循环。
"""
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# 复用连接池，避免每次请求都建立新连接
_async_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    """懒加载单例 AsyncClient（自带连接池）"""
    global _async_client
    if _async_client is None:
        _async_client = httpx.AsyncClient(timeout=15)
    return _async_client


async def get_embedding(text: str) -> list[float]:
    """
    将文本转为 1024 维向量 (BAAI/bge-m3)

    Args:
        text: 待向量化的文本（建议 < 1500 字符）

    Returns:
        1024 维 float 列表
    """
    headers = {
        "Authorization": f"Bearer {settings.GUIJI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.GUIJI_EMB_MODEL,
        "input": text[:1500],
        "encoding_format": "float",
    }

    client = _get_client()
    resp = await client.post(
        settings.GUIJI_EMB_URL, headers=headers, json=payload
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]
