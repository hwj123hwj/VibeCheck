"""
歌曲相关接口
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db, Song
from app.schemas import SongDetail, SongBase

router = APIRouter()

# 网易云歌词 API (返回 LRC 格式，带时间戳)
_NETEASE_LRC_API = "http://music.163.com/api/song/lyric"
# 网易云音频外链模板
_NETEASE_AUDIO_URL = "https://music.163.com/song/media/outer/url?id={song_id}.mp3"


@router.get("/songs/{song_id}", response_model=SongDetail)
async def get_song(song_id: str, db: Session = Depends(get_db)):
    """获取单首歌曲详情"""
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    return song


@router.get("/songs/{song_id}/lrc")
async def get_song_lrc(song_id: str, db: Session = Depends(get_db)):
    """
    获取歌曲的 LRC 格式歌词 (带时间戳)，用于前端同步滚动播放。

    返回示例:
    {
        "id": "1234",
        "lrc": "[00:00.00]歌名 - 歌手\\n[00:12.34]第一句歌词\\n...",
        "tlyric": "[00:12.34]First line translation\\n..."  // 翻译歌词，可能为空
    }
    """
    # 先确认歌曲存在
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # 从网易云 API 实时获取带时间戳的 LRC 歌词
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                _NETEASE_LRC_API,
                params={"id": song_id, "lv": 1, "kv": 1, "tv": -1},
                headers={"Referer": "https://music.163.com/"},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to fetch LRC from upstream")

    lrc_text = ""
    tlyric_text = ""
    if "lrc" in data and data["lrc"].get("lyric"):
        lrc_text = data["lrc"]["lyric"]
    if "tlyric" in data and data["tlyric"].get("lyric"):
        tlyric_text = data["tlyric"]["lyric"]

    return {"id": song_id, "lrc": lrc_text, "tlyric": tlyric_text}


@router.get("/songs/{song_id}/audio")
async def proxy_song_audio(song_id: str):
    """
    代理音频流 — 解决浏览器直接请求网易云 MP3 被 Referer/CORS 拦截的问题。
    策略: 外链优先 → enhance API 兜底 → VIP 歌曲报错。
    使用流式传输避免将整个音频文件读入内存。
    """
    _headers = {
        "Referer": "https://music.163.com/",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    # 使用流式请求，避免大文件内存占用
    client = httpx.AsyncClient(timeout=30, follow_redirects=True)
    handoff_to_stream = False

    try:
        # ① 尝试外链 (大部分免费歌曲可用)
        outer_url = _NETEASE_AUDIO_URL.format(song_id=song_id)
        try:
            resp = await client.send(
                client.build_request("GET", outer_url, headers=_headers),
                stream=True,
            )
            ct = resp.headers.get("content-type", "")
            if resp.status_code == 200 and ("audio" in ct or "octet" in ct):
                handoff_to_stream = True
                return _make_streaming_response(resp, client)
            await resp.aclose()
        except httpx.HTTPError:
            pass

        # ② 外链失败，用 enhance/player/url API 获取 CDN 直链
        try:
            api_resp = await client.get(
                "http://music.163.com/api/song/enhance/player/url",
                params={"id": song_id, "ids": f"[{song_id}]", "br": 320000},
                headers=_headers,
            )
            data = api_resp.json()
            cdn_url = data.get("data", [{}])[0].get("url")
            if cdn_url:
                audio_resp = await client.send(
                    client.build_request("GET", cdn_url, headers=_headers),
                    stream=True,
                )
                if audio_resp.status_code == 200:
                    handoff_to_stream = True
                    return _make_streaming_response(audio_resp, client)
                await audio_resp.aclose()
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            pass

        # ③ 两种方式都失败 — 大概率是 VIP 歌曲
        raise HTTPException(
            status_code=404,
            detail="该歌曲暂不可播放（可能是 VIP 专属歌曲）",
        )
    finally:
        if not handoff_to_stream:
            await client.aclose()


def _make_streaming_response(
    resp: httpx.Response, client: httpx.AsyncClient
) -> StreamingResponse:
    """把上游音频流式转发给前端，读完后关闭连接和客户端。"""
    content_type = resp.headers.get("content-type", "audio/mpeg")
    headers: dict[str, str] = {"Accept-Ranges": "bytes"}
    cl = resp.headers.get("content-length")
    if cl:
        headers["Content-Length"] = cl

    async def _stream_iter():
        try:
            async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                yield chunk
        finally:
            await resp.aclose()
            await client.aclose()

    return StreamingResponse(
        _stream_iter(),
        media_type=content_type,
        headers=headers,
    )


@router.get("/songs/random/list", response_model=list[SongBase])
async def get_random_songs(count: int = 12, db: Session = Depends(get_db)):
    """随机获取歌曲（首页发现用）"""
    songs = (
        db.query(Song)
        .filter(
            Song.is_duplicate == False,
            Song.review_text != None,
        )
        .order_by(func.random())
        .limit(count)
        .all()
    )
    return songs
