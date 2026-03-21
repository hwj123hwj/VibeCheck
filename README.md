# VibeCheck - 混合音乐推荐系统

> 懂你的情绪，更懂你的歌

VibeCheck 是一个基于 **LLM 语义评语 + 歌词向量 + TF-IDF** 的混合音乐推荐系统（毕业设计）。核心创新：用大模型生成的"乐评" Embedding 替代传统情感分类，实现对歌曲深层意境的语义检索与推荐。

**在线体验：[music.weijian.online](https://music.weijian.online)**

## 核心特性

- **多模式语义搜索** — 自动识别 / 心情氛围 / 搜歌词 / 搜歌名 / 搜歌手，按需切换，精准高效
- **三路混合融合** — 评语向量 + 精华歌词向量 + TF-IDF 关键词，权重可动态调节
- **AI 情感分析** — LLM 为每首歌生成结构化评语、意境标签（vibe_tags）、情感维度评分（vibe_scores）
- **动态推荐权重** — 歌曲详情页支持实时拖拽调整三路权重，演示不同参数下的推荐效果
- **同名歌曲去重** — 推荐结果支持按主标题模糊去重，过滤各版本重复歌曲
- **50,000+ 华语歌曲** — 全量歌词、AI 评语、双向量索引

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 · Vite · Lucide Icons |
| 后端 | Python 3.12 · FastAPI · SQLAlchemy 2.0 |
| 数据库 | PostgreSQL 17 + pgvector (HNSW 索引) |
| LLM | LongMao (LongCat-Flash-Chat) |
| Embedding | 硅基流动 BAAI/bge-m3 (1024 维) |
| NLP | Jieba + scikit-learn TF-IDF |
| 部署 | Nginx · GitHub Actions CI/CD · 腾讯云 EdgeOne CDN |

## 项目结构

```
VibeCheck/
├── app/                          # FastAPI 后端 API
│   ├── main.py                   # 应用入口
│   ├── config.py                 # 配置管理
│   ├── database.py               # 数据库连接 & ORM 模型
│   ├── schemas.py                # Pydantic 请求/响应模型
│   ├── routers/                  # API 路由
│   │   ├── songs.py              # 歌曲详情、随机发现、情绪分区
│   │   ├── search.py             # 多模式语义搜索
│   │   └── recommend.py          # 单曲推荐（动态权重 + 去重）
│   └── services/                 # 业务逻辑
│       ├── embedding.py          # 向量化服务
│       ├── llm.py                # LLM 意图路由
│       ├── search.py             # 混合搜索核心
│       └── recommend.py          # 相似推荐核心
│
├── frontend/                     # React 前端
│   ├── src/
│   │   ├── pages/                # 首页、搜索页、歌曲详情页
│   │   ├── components/           # 全局播放器、歌词滚动、雷达图等
│   │   ├── context/              # 播放器状态、搜索缓存
│   │   └── api/                  # Axios 请求封装
│   └── vite.config.js
│
├── deploy_crawler/               # 数据采集 & 特征工程
│   ├── docker-compose.yml        # PostgreSQL + 爬虫容器编排
│   ├── db_init.py                # 数据库初始化
│   ├── app.py                    # 爬虫主程序
│   ├── batch_ai_analysis.py      # LLM 批量分析
│   ├── batch_vectorization.py    # 评语向量化
│   ├── batch_lyrics_vectorization.py  # 歌词向量化
│   ├── compute_tfidf.py          # 分词 + TF-IDF
│   ├── extract_core_lyrics.py    # 核心歌词提取
│   └── migrations/
│       └── run_hnsw_migration.py # pgvector HNSW 索引迁移
│
├── docs/                         # 项目文档
├── deploy.sh                     # 服务器一键部署脚本
└── pyproject.toml                # Python 项目配置 (uv)
```

## 快速开始

### 1. 环境准备

```bash
# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库连接和 API Keys
```

### 2. 启动数据库

```bash
cd deploy_crawler
docker-compose up -d db
```

### 3. 启动后端

```bash
uv run uvicorn app.main:app --reload --port 8000
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173，后端 Swagger 文档：http://localhost:8000/docs

## API 接口

| 接口 | 说明 |
|------|------|
| `GET /api/search?q=下雨天伤感的歌&mode=auto` | 多模式语义搜索（auto/vibe/lyrics/title/artist） |
| `GET /api/recommend/{song_id}?w_review=0.5&w_lyrics=0.4&w_tfidf=0.1&dedupe=false` | 单曲推荐（动态权重 + 可选去重） |
| `GET /api/songs/{song_id}` | 歌曲详情 |
| `GET /api/songs/{song_id}/lrc` | LRC 歌词（带时间戳） |
| `GET /api/songs/random/list` | 随机发现 |
| `GET /api/songs/vibe-sections` | 首页情绪分区 |

## 文档

- [需求文档 (PRD)](docs/PRD.md)
- [系统架构设计](docs/SYSTEM_ARCHITECTURE.md)
- [用户画像设计](docs/USER_PROFILE_DESIGN.md)
- [毕设改进计划](docs/THESIS_IMPROVEMENT.md)
- [产品规划](docs/product_roadmap.md)

## License

MIT
