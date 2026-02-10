"""
Embedding 服务 - 调用硅基流动 BAAI/bge-m3

封装向量化调用逻辑，供搜索和推荐服务使用。
"""
import requests
from app.config import get_settings

settings = get_settings()


def get_embedding(text: str) -> list[float]:
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

    resp = requests.post(
        settings.GUIJI_EMB_URL, headers=headers, json=payload, timeout=15
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]
