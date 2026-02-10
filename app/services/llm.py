"""
LLM 服务 - 调用 LongMao (LongCat-Flash-Chat)

用于：
1. 搜索意图路由 (intent routing)
2. 未来的动态评语生成
"""
import json
from openai import OpenAI
from app.config import get_settings

settings = get_settings()

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.LONGMAO_API_KEY,
            base_url=settings.LONGMAO_BASE_URL,
        )
    return _client


def parse_search_intent(query: str) -> dict:
    """
    使用 LLM 解析用户搜索意图

    Returns:
        {
            "artist": str | None,
            "title": str | None,
            "vibe": str,         # 纯化后的情感/场景描述
            "type": "exact" | "lyrics" | "vibe"
        }
    """
    prompt = f"""你是一个音乐搜索意图解析引擎。请将用户的输入拆解为 JSON 格式。
输入："{query}"
要求：
1. artist: 提取歌手名，没有则为 null。
2. title: 提取歌名，没有则为 null。
3. vibe: 提取纯粹的心情、场景或歌词描述，并统一转换为【简体中文】。
4. type: "exact" (如果有明确歌手或歌名), "lyrics" (如果是歌词残句), "vibe" (纯搜感觉)。
只输出 JSON。"""

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=settings.LONGMAO_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception:
        # LLM 不可用时降级为纯 vibe 搜索
        return {"artist": None, "title": None, "vibe": query, "type": "vibe"}
