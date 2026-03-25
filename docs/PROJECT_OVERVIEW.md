# VibeCheck 项目全貌

> 在线地址：[music.weijian.online](https://music.weijian.online)

---

## 一、项目定位

VibeCheck 是一个华语音乐语义搜索与推荐系统。

核心创新：**不用情感分类打分，而是让 LLM 给每首歌写一段"乐评"，把乐评向量化后做语义检索**。搜"深夜一个人 emo"，系统找的不是关键词匹配，而是语义上和这种情绪最接近的歌。

数据规模：**50,000+ 首华语歌曲**，每首都有 AI 乐评、双向量索引、TF-IDF 关键词。

---

## 二、整体架构

```
用户浏览器
    │ HTTPS
    ▼
腾讯云 EdgeOne CDN（SSL 终止，回源 HTTP）
    │
    ▼
Nginx（80 端口，反向代理）
    ├── /          → 前端静态文件 /var/www/vibecheck
    └── /api/      → FastAPI 后端 8000 端口
            │
            ├── PostgreSQL 17 + pgvector（向量检索）
            └── 外部 API
                  ├── 硅基流动 BAAI/bge-m3（Embedding）
                  ├── LongMao LongCat-Flash-Lite（LLM 意图解析）
                  └── 网易云 API（LRC 歌词、音频代理）
```

**部署方式**：GitHub Actions 监听 master 分支，push 后自动 rsync 到服务器并执行 `deploy.sh`。`deploy.sh` 负责安装依赖、构建前端、重启 uvicorn、配置 Nginx，做了依赖哈希缓存，未变动时跳过安装。

---

## 三、数据库 Schema

```sql
-- 核心表，全部数据在此，无其他业务表
CREATE TABLE songs (
    id               VARCHAR(50)   PRIMARY KEY,   -- 网易云歌曲 ID
    title            VARCHAR(255)  NOT NULL,
    artist           VARCHAR(255)  NOT NULL,
    lyrics           TEXT,                        -- 原始歌词（已去时间戳）
    segmented_lyrics TEXT,                        -- jieba 分词后（用于 TF-IDF）
    core_lyrics      TEXT,                        -- 提取的副歌/金句
    review_text      TEXT,                        -- LLM 生成的乐评
    vibe_tags        JSONB,                       -- 意境标签 ["深夜","孤独"]
    vibe_scores      JSONB,                       -- 情感维度 {loneliness:0.8,...}
    recommend_scene  TEXT,                        -- 推荐收听场景
    review_vector    VECTOR(1024),               -- 乐评 Embedding（主检索向量）
    lyrics_vector    VECTOR(1024),               -- core_lyrics Embedding
    tfidf_vector     JSONB,                       -- Top-10 关键词+权重
    album_cover      VARCHAR(500),
    is_duplicate     BOOLEAN       DEFAULT FALSE, -- 翻唱/Live 标记
    created_at       TIMESTAMP,
    updated_at       TIMESTAMP
);

-- HNSW 向量索引（已建，检索 ~100ms）
CREATE INDEX idx_review_vector_hnsw ON songs
    USING hnsw (review_vector vector_cosine_ops) WITH (m=16, ef_construction=64);
CREATE INDEX idx_lyrics_vector_hnsw ON songs
    USING hnsw (lyrics_vector vector_cosine_ops) WITH (m=16, ef_construction=64);
```

---

## 四、后端结构

```
app/
├── main.py          # FastAPI 入口，注册路由和 CORS
├── config.py        # pydantic-settings，读取 .env
├── database.py      # asyncpg 异步连接池，SQLAlchemy ORM
├── schemas.py       # Pydantic 请求/响应模型
├── routers/
│   ├── songs.py     # 歌曲详情、随机列表、情绪分区、LRC、音频代理
│   ├── search.py    # 语义搜索（多模式）
│   └── recommend.py # 单曲推荐（动态权重+去重）
└── services/
    ├── embedding.py # httpx 异步调用硅基流动
    ├── llm.py       # 异步调用 LongMao，解析搜索意图
    ├── search.py    # 混合搜索核心逻辑
    └── recommend.py # 推荐核心逻辑 + 内存缓存
```

### 路由注意事项

`songs.py` 中 `/songs/random/list` 和 `/songs/vibe-sections` **必须定义在** `/songs/{song_id}` **之前**，否则 FastAPI 会把 `random` 和 `vibe-sections` 当作 song_id 匹配，返回 404。

---

## 五、搜索系统

### 五个搜索模式

| 模式 key | 含义 | 后端逻辑 | 跳过什么 |
|---|---|---|---|
| `auto` | 自动识别 | LLM 解析意图后路由 | 无 |
| `vibe` | 心情氛围 | 纯 review_vector 语义检索 | LLM |
| `lyrics` | 搜歌词 | lyrics_vector + 关键词混合 | LLM |
| `title` | 搜歌名 | `title ILIKE '%xxx%'` | LLM + Embedding |
| `artist` | 搜歌手 | `artist ILIKE '%xxx%'` | LLM + Embedding |

### 混合检索公式（auto/vibe/lyrics 模式）

```
FinalScore = review_sim × w_review
           + lyrics_sim × w_lyrics
           + tfidf_overlap × w_rational
```

三套权重配置（auto 模式由 LLM 路由决定用哪套）：

| 意图类型 | w_review | w_lyrics | w_rational |
|---|---|---|---|
| vibe（氛围） | 0.7 | 0.3 | 0.0 |
| lyrics（歌词） | 0.2 | 0.6 | 0.2 |
| exact（精确） | 0.1 | 0.1 | 0.8 |

### TF-IDF 重叠率计算说明

`tfidf_overlap` 不是传统 TF-IDF 打分，而是**关键词集合交集比例**：

```
tfidf_overlap = 候选歌曲关键词与查询词的重合数 / 查询词总数
```

查询词来源：搜索时对 query 做 jieba 分词（auto 模式），或源歌曲的 Top-20 TF-IDF 关键词（推荐时）。

---

## 六、推荐系统

### 接口参数

```
GET /api/recommend/{song_id}
    ?top_k=6          # 返回数量
    &w_review=0.5     # 评语向量权重
    &w_lyrics=0.4     # 歌词向量权重
    &w_tfidf=0.1      # TF-IDF 关键词权重
    &dedupe=false     # 是否按歌名去重
```

三个权重之和应为 1.0，前端通过两个滑条控制（第三个自动补足）。

### 缓存策略

内存 TTLCache，TTL=10 小时，maxsize=500。

**cache key = (song_id, top_k, w_review, w_lyrics, w_tfidf)**，不含 dedupe。

固定多取 `top_k × 5` 条候选缓存，去重只是对缓存列表做 Python 过滤，切换 dedupe 不触发新的数据库查询。

### 去重逻辑

按**主标题**模糊去重，不是精确匹配 title 字段：

```python
def _base_title(title):
    t = 去掉括号内容          # "安和桥（DJ版）" → "安和桥"
    t = 去掉版本关键词         # "安和桥 Live"   → "安和桥"
    t = 去掉空格后内容         # "老男孩 筷子兄弟" → "老男孩"
    return t.strip()
```

源歌曲自身的主标题也被预先加入去重集合，避免推荐同名歌曲。

---

## 七、前端结构

```
frontend/src/
├── App.jsx
├── main.jsx
├── api/client.js          # Axios 实例，统一接口封装
├── pages/
│   ├── HomePage.jsx        # 随机发现 + 情绪分区
│   ├── SearchPage.jsx      # 搜索结果页（含缓存，返回不重新请求）
│   └── SongDetailPage.jsx  # 歌曲详情（播放器、歌词滚动、推荐权重面板）
├── components/
│   ├── GlobalPlayer.jsx    # 全局悬浮播放器（跨页面持续播放）
│   ├── Layout.jsx
│   ├── LyricsScroller.jsx  # LRC 同步滚动歌词
│   ├── SearchInput.jsx     # 搜索框（含模式下拉）
│   ├── SongCard.jsx        # 卡片（含评分 badge 和三路进度条）
│   └── VibeRadarChart.jsx  # 情感五维雷达图
├── context/
│   ├── PlayerContext.jsx   # 全局播放状态
│   └── SearchContext.jsx   # 搜索结果缓存（useRef，跨页面保持）
└── utils/parseLrc.js       # LRC 时间戳解析
```

### 音频播放方案

1. 前端请求 `/api/songs/{id}/audio`
2. 后端用 `httpx` 带合法 Referer 请求网易云，以 `StreamingResponse` 64KB 分块转发
3. VIP 歌曲两级探测均失败后返回 404，前端显示"VIP 歌曲"提示并附网易云跳转链接

---

## 八、关键配置

`.env` 文件（不提交 Git）：

```
DB_USER=root
DB_PASSWORD=...
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=music_db

GUIJI_API_KEY=...        # 硅基流动 Embedding
LONGMAO_API_KEY=...      # LongMao LLM
LONGMAO_MODEL=LongCat-Flash-Lite
```

默认权重可通过环境变量覆盖：
```
SEARCH_SCORE_THRESHOLD=0.45
SEARCH_WEIGHT_VIBE={"review":0.7,"lyrics":0.3,"rational":0.0}
```

---

## 九、本地开发

```bash
# 后端
uv sync
uv run uvicorn app.main:app --reload --port 8000

# 前端
cd frontend && npm install && npm run dev
# 访问 http://localhost:5173，/api 自动代理到 8000
```

数据库在远端服务器，本地开发需要在 `.env` 中配置正确的连接信息，或使用 SSH 隧道。
