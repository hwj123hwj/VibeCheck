# VibeCheck - 混合音乐推荐系统

> 懂你的情绪，更懂你的歌

VibeCheck 是一个基于 **LLM 语义评语 + TF-IDF** 的混合音乐推荐系统（毕业设计）。核心创新：用大模型生成的"乐评" Embedding 替代传统情感分类，实现对歌曲深层意境的语义检索。

## 核心特性

- **"说人话"搜歌** — 自然语言描述心情/场景/故事，语义检索匹配歌曲
- **三路混合融合** — 评语向量 + 精华歌词向量 + TF-IDF 关键词，加权排序
- **AI 情感分析** — LLM 为每首歌生成结构化评语、意境标签 (vibe_tags)、情感维度评分 (vibe_scores)
- **10,000+ 华语歌曲** — 全量歌词、AI 评语、双向量索引

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.12 · FastAPI · SQLAlchemy 2.0 |
| 数据库 | PostgreSQL 17 + pgvector |
| LLM | LongMao (LongCat-Flash-Chat) |
| Embedding | 硅基流动 BAAI/bge-m3 (1024维) |
| NLP | Jieba + scikit-learn TF-IDF |
| 部署 | Docker + docker-compose |
| 前端 | React + Vite + Tailwind CSS *(开发中)* |

## 项目结构

```
VibeCheck/
├── app/                          # FastAPI 后端 API
│   ├── main.py                   # 应用入口
│   ├── config.py                 # 配置管理
│   ├── database.py               # 数据库连接 & ORM 模型
│   ├── schemas.py                # Pydantic 请求/响应模型
│   ├── routers/                  # API 路由
│   │   ├── songs.py              # 歌曲详情 & 随机发现
│   │   ├── search.py             # 语义搜索
│   │   └── recommend.py          # 单曲推荐
│   └── services/                 # 业务逻辑
│       ├── embedding.py          # 硅基流动向量化
│       ├── llm.py                # LLM 意图路由
│       ├── search.py             # 混合搜索核心
│       └── recommend.py          # 相似推荐核心
│
├── deploy_crawler/               # 数据采集 & 特征工程 (Docker 部署包)
│   ├── docker-compose.yml        # 容器编排 (PostgreSQL + 爬虫)
│   ├── Dockerfile
│   ├── db_init.py                # 数据库模型 & 初始化
│   ├── app.py                    # 爬虫主程序
│   ├── batch_ai_analysis.py      # LLM 批量分析
│   ├── batch_vectorization.py    # 评语向量化
│   ├── batch_lyrics_vectorization.py  # 歌词向量化
│   ├── compute_tfidf.py          # 分词 + TF-IDF
│   ├── extract_core_lyrics.py    # 核心歌词提取算法
│   └── ...
│
├── docs/                         # 项目文档
│   ├── PRD.md                    # 需求文档
│   ├── product_roadmap.md        # 产品规划
│   ├── DEVELOPMENT_STATUS.md     # 已完成状态
│   └── NEXT_STEPS.md             # 下一步开发计划
│
└── pyproject.toml                # Python 项目配置 (uv)
```

## 快速开始

### 1. 环境准备

```bash
# 安装依赖 (使用 uv)
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Keys
```

### 2. 启动数据库

```bash
cd deploy_crawler
docker-compose up -d db
```

### 3. 启动 API 服务

```bash
uv run uvicorn app.main:app --reload --port 8000
```

访问 http://localhost:8000/docs 查看 Swagger API 文档。

### API 接口

| 接口 | 说明 |
|------|------|
| `GET /api/search?q=下雨天伤感的歌` | 语义搜索 |
| `GET /api/recommend/{song_id}` | 单曲推荐 |
| `GET /api/songs/{song_id}` | 歌曲详情 |
| `GET /api/songs/random/list` | 随机发现 |

## 文档

- [需求文档 (PRD)](docs/PRD.md)
- [产品规划](docs/product_roadmap.md)
- [开发完成状态](docs/DEVELOPMENT_STATUS.md)
- [下一步计划](docs/NEXT_STEPS.md)

## License

MIT
