# VibeCheck 后端优化修复记录

> **日期**：2026-02-11  
> **影响范围**：后端 API 性能、搜索可解释性、代码规范化

---

## 修复总览

| # | 问题 | 影响 | 解决方案 | 涉及文件 |
|---|------|------|----------|----------|
| 1 | Embedding 服务阻塞事件循环 | 搜索卡顿、高并发超时 | 同步 `requests` → 异步 `httpx.AsyncClient` | `app/services/embedding.py` |
| 2 | 推荐算法缺失 TF-IDF 权重 | 公式与注释不一致，推荐质量下降 | 补全 JSONB key 交集计算 | `app/services/recommend.py` |
| 3 | 搜索结果缺少可解释性 | 用户不知道"为什么推荐这首歌" | 返回三路子分数 + 前端进度条 | `app/schemas.py`, `app/services/search.py`, `frontend/src/components/SongCard.jsx` |
| 4 | 音频代理假流式传输 | 大文件占满内存 | 真流式 `aiter_bytes(64KB)` | `app/routers/songs.py` |
| 5 | 搜索阈值硬编码 | 无法动态调参 | 提取到 `config.py` | `app/config.py`, `app/services/search.py` |
| 6 | LLM 降级无日志 | 生产排错困难 | 增加 logging + 区分异常类型 | `app/services/llm.py` |
| 7 | 向量检索全表扫描 | 5.3w 数据检索 1~2s | 创建 HNSW 索引 | `deploy_crawler/migrations/001_create_hnsw_indexes.sql` |

---

## 详细说明

### 1. Embedding 服务阻塞事件循环

**问题**：`embedding.py` 使用同步的 `requests.post()`，在 FastAPI 异步框架中会阻塞整个事件循环，导致其他请求排队等待。

**影响**：搜索接口响应时间不稳定，高并发时出现超时。

**解决方案**：
```python
# Before (阻塞)
import requests
def get_embedding(text: str) -> list[float]:
    resp = requests.post(url, json=payload, timeout=15)
    return resp.json()["data"][0]["embedding"]

# After (异步 + 连接池复用)
import httpx
_async_client: httpx.AsyncClient | None = None

async def get_embedding(text: str) -> list[float]:
    client = _get_client()  # 单例连接池
    resp = await client.post(url, json=payload)
    return resp.json()["data"][0]["embedding"]
```

---

### 2. 推荐算法缺失 TF-IDF 权重

**问题**：`recommend.py` 注释声称使用 `0.5 * review + 0.4 * lyrics + 0.1 * TF-IDF`，但代码只计算了前两项，缺失的 0.1 权重被丢弃。

**影响**：推荐结果与算法设计不符，关键词相关性未被考虑。

**解决方案**：
```python
# 提取源歌曲的 TF-IDF 关键词
src_tfidf_keys = list(source.tfidf_vector.keys()) if source.tfidf_vector else []

# 构建 SQL：统计目标歌曲命中源关键词的数量
overlap_parts = " + ".join(
    f"CASE WHEN tfidf_vector ? '{kw}' THEN 1 ELSE 0 END"
    for kw in src_tfidf_keys[:20]
)
tfidf_overlap_expr = f"({overlap_parts})::float / {len(src_tfidf_keys[:20])}"

# ORDER BY 补上 0.1 权重
ORDER BY review_sim * 0.5 + lyrics_sim * 0.4 + {tfidf_overlap_expr} * 0.1 DESC
```

---

### 3. 搜索结果缺少可解释性

**问题**：搜索 API 只返回 `final_score`，用户无法理解"为什么这首歌排在前面"。

**影响**：论文的"算法可解释性"论点缺乏支撑，用户体验不够透明。

**解决方案**：

**后端** — `schemas.py` 扩展字段：
```python
class SongSearchResult(SongBase):
    score: float = 0.0
    # 新增：可解释性三路子分数
    review_score: Optional[float] = None   # 评语语义匹配度
    lyrics_score: Optional[float] = None   # 歌词语义匹配度
    rational_score: Optional[float] = None # 关键词/精确匹配
```

**前端** — `SongCard.jsx` 展示进度条：
```jsx
{song.review_score != null && (
  <div>
    <ScoreBar label="评语语义" value={song.review_score} color="var(--accent-pink)" />
    <ScoreBar label="歌词语义" value={song.lyrics_score} color="var(--accent-yellow)" />
    <ScoreBar label="关键词" value={song.rational_score} color="#8EC5FC" />
  </div>
)}
```

---

### 4. 音频代理假流式传输

**问题**：`songs.py` 的 `_make_audio_response()` 使用 `iter([resp.content])`，实际上先把整个音频（可能 10MB+）读入内存再返回。

**影响**：高并发时内存暴涨，可能导致 OOM。

**解决方案**：
```python
# Before (假流式)
return StreamingResponse(iter([resp.content]), media_type="audio/mpeg")

# After (真流式，64KB 分块)
async def _stream_iter():
    try:
        async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
            yield chunk
    finally:
        await resp.aclose()
        await client.aclose()

return StreamingResponse(_stream_iter(), media_type="audio/mpeg")
```

---

### 5. 搜索阈值硬编码

**问题**：`search.py` 中 `WHERE review_score > 0.4` 直接写死，无法在生产环境动态调整。

**影响**：调参需要改代码并重新部署。

**解决方案**：

**config.py 新增配置**：
```python
class Settings(BaseSettings):
    # 搜索参数（支持环境变量覆盖）
    SEARCH_SCORE_THRESHOLD: float = 0.4
    SEARCH_WEIGHT_VIBE: dict = {"review": 0.6, "lyrics": 0.2, "rational": 0.2}
    SEARCH_WEIGHT_LYRICS: dict = {"review": 0.2, "lyrics": 0.6, "rational": 0.2}
    SEARCH_WEIGHT_EXACT: dict = {"review": 0.1, "lyrics": 0.1, "rational": 0.8}
```

**search.py 使用配置**：
```python
WHERE review_score > :threshold OR lyrics_score > :threshold
# ...
"threshold": settings.SEARCH_SCORE_THRESHOLD
```

---

### 6. LLM 降级无日志

**问题**：`llm.py` 的异常处理是空的 `except Exception`，降级时没有任何日志，生产排错困难。

**影响**：LLM 服务挂了也无法从日志中发现。

**解决方案**：
```python
import logging
logger = logging.getLogger(__name__)

try:
    result = json.loads(response.choices[0].message.content)
    logger.info(f"LLM intent parsed: query='{query}' -> type={result.get('type')}")
    return result
except json.JSONDecodeError as e:
    logger.warning(f"LLM returned invalid JSON for query '{query}': {e}")
    return {"artist": None, "title": None, "vibe": query, "type": "vibe"}
except Exception as e:
    logger.warning(f"LLM intent parsing failed, falling back: {type(e).__name__}: {e}")
    return {"artist": None, "title": None, "vibe": query, "type": "vibe"}
```

---

### 7. 向量检索全表扫描 (HNSW 索引)

**问题**：5.3w+ 条数据，每次搜索都要计算所有向量的余弦距离，耗时 1~2 秒。

**影响**：搜索体验卡顿，演示效果不佳。

**解决方案**：创建 HNSW (Hierarchical Navigable Small World) 近似最近邻索引。

```sql
-- 评语向量索引
CREATE INDEX IF NOT EXISTS idx_review_vector_hnsw
  ON songs USING hnsw (review_vector vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- 歌词向量索引
CREATE INDEX IF NOT EXISTS idx_lyrics_vector_hnsw
  ON songs USING hnsw (lyrics_vector vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

**执行结果**：
- `idx_review_vector_hnsw` — 421 MB，创建耗时 122.8s
- `idx_lyrics_vector_hnsw` — 418 MB，创建耗时 146.0s
- 检索性能：1~2s → **100ms 级**

---

## 文件变更清单

```
app/
├── config.py           # +6 行：搜索参数配置
├── schemas.py          # +4 行：可解释性字段
├── routers/
│   └── songs.py        # 重构音频流式传输
└── services/
    ├── embedding.py    # 同步→异步改造
    ├── llm.py          # 增加日志
    ├── recommend.py    # 补全 TF-IDF 计算
    └── search.py       # 使用 config + 返回子分数

frontend/src/components/
└── SongCard.jsx        # +60 行：ScoreBar 组件

deploy_crawler/migrations/
├── 001_create_hnsw_indexes.sql  # SQL 迁移脚本
└── run_hnsw_migration.py        # Python 执行脚本
```

---

*Generated @ 2026-02-11*
