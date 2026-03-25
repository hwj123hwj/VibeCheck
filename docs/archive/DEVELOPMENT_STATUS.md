# VibeCheck 开发完成状态报告

> 最后更新：2026-02-10
> 项目版本：v0.1.0 (数据工程 + 特征工程阶段)

---

## 一、项目概述

VibeCheck 是一个**基于 LLM 语义评语与 TF-IDF 的混合音乐推荐系统**，毕设课题。核心创新在于用 LLM 生成的"乐评"Embedding 替代传统的情感分类打分，实现对歌曲深层情感意境的语义检索。

---

## 二、已完成模块总览

### ✅ 阶段一：数据工程 (Data Engineering) — 100% 完成

| 模块 | 文件 | 说明 | 状态 |
|------|------|------|------|
| 数据库设计 | `deploy_crawler/db_init.py` | PostgreSQL + pgvector，完整的 `songs` 表 ORM 模型 | ✅ |
| 全量爬虫 | `deploy_crawler/app.py` | Requests+BS4 长效流水线，54 页华语歌单 (~1890 歌单)，逐页抓取歌曲 & 歌词入库 | ✅ |
| 数据去重 | `deploy_crawler/mark_duplicates.py` | 按歌词内容分组，评分保留最优版本，标记翻唱/Live/Remix 为 `is_duplicate=True` | ✅ |
| Docker 部署 | `deploy_crawler/Dockerfile` + `docker-compose.yml` | PostgreSQL (pgvector/pg17) + Python 爬虫容器，一键 `docker-compose up` | ✅ |

**数据规模**：约 10,000+ 首华语歌曲（含歌词），存储在 PostgreSQL 中。

### ✅ 阶段二：特征工程 (Feature Engineering) — 100% 完成

| 模块 | 文件 | 说明 | 状态 |
|------|------|------|------|
| **感性特征 - AI 评语生成** | `deploy_crawler/batch_ai_analysis.py` | 调用 LongMao LLM 生成结构化 JSON 分析（vibe_tags、emotional_scores、review、scene） | ✅ |
| **感性特征 - 评语向量化** | `deploy_crawler/batch_vectorization.py` | 拼接 Tags+Review+Scene → 硅基流动 BAAI/bge-m3 → 1024 维 `review_vector` | ✅ |
| **理性特征 - 分词 & TF-IDF** | `deploy_crawler/compute_tfidf.py` | Jieba 分词 → sklearn TfidfVectorizer(max_features=20000) → JSONB 关键词 Top10 | ✅ |
| **核心歌词提取** | `deploy_crawler/extract_core_lyrics.py` + `batch_update_core_lyrics.py` | 高频行检测 + 长度过滤，提取副歌/金句 → `core_lyrics` 字段 | ✅ |
| **歌词向量化** | `deploy_crawler/batch_lyrics_vectorization.py` | 对 `core_lyrics` 进行 Embedding → 1024 维 `lyrics_vector` | ✅ |

### ✅ 混合检索原型验证 — 已验证可行

| 模块 | 文件 | 说明 | 状态 |
|------|------|------|------|
| **混合搜索测试** | `deploy_crawler/hybrid_search_test.py` | 完整的混合检索原型：LLM 意图路由 → 双向量召回(review_vector + lyrics_vector) + TF-IDF 关键词匹配 → 加权融合排序 | ✅ 原型 |

### ✅ 运维自动化 — 已配置

| 模块 | 文件 | 说明 |
|------|------|------|
| 每日 AI 分析 | `daily_ai_analysis.sh` | crontab 定时任务，自动执行 batch_ai_analysis.py |
| 歌词提取 + 向量化 | `run_extract_background.sh` | 后台执行 core_lyrics 提取和 lyrics 向量化 |

---

## 三、数据库 Schema 最终状态

```
表名: songs (PostgreSQL + pgvector)
─────────────────────────────────────────────────────────
字段名              类型            说明
─────────────────────────────────────────────────────────
id                  VARCHAR(50)     PK, 网易云歌曲 ID
title               VARCHAR(255)    歌曲标题
artist              VARCHAR(255)    歌手
lyrics              TEXT            原始歌词 (已清洗时间轴)
segmented_lyrics    TEXT            Jieba 分词后的歌词
core_lyrics         TEXT            精华歌词 (副歌/高频行)
review_text         TEXT            LLM 生成的情感评语
vibe_tags           JSONB           意境标签 (如 ["深夜","孤独","治愈"])
vibe_scores         JSONB           情感维度评分 (loneliness, energy, healing...)
recommend_scene     TEXT            推荐收听场景
review_vector       VECTOR(1024)    评语 Embedding (BAAI/bge-m3)
lyrics_vector       VECTOR(1024)    精华歌词 Embedding (BAAI/bge-m3)
tfidf_vector        JSONB           TF-IDF 关键词 Top10 + 权重
album_cover         VARCHAR(500)    专辑封面 URL
is_duplicate        BOOLEAN         是否为重复歌曲
created_at          TIMESTAMP       入库时间
updated_at          TIMESTAMP       最后更新时间
─────────────────────────────────────────────────────────
```

---

## 四、技术栈确认

| 层级 | 技术 | 用途 |
|------|------|------|
| 语言 | Python 3.12 | 全栈开发 |
| 依赖管理 | uv | 替代 pip/poetry |
| 数据库 | PostgreSQL 17 + pgvector | 关系存储 + 向量检索 |
| ORM | SQLAlchemy 2.0 | 数据库操作 |
| 爬虫 | Requests + BeautifulSoup4 | 服务端无浏览器爬取 |
| NLP | Jieba + scikit-learn | 中文分词 + TF-IDF |
| LLM | LongMao (LongCat-Flash-Chat) | 情感评语生成 |
| Embedding | 硅基流动 BAAI/bge-m3 (1024维) | 语义向量化 |
| 容器化 | Docker + docker-compose | 服务器部署 |

---

## 五、清理记录 (2026-02-10)

本次清理删除了 **14 个**已完成历史使命的中间文件：

### 已删除 — 根目录 (被 deploy_crawler/app.py 取代的爬虫迭代)
- `crawler.py` — v1 本地 Selenium 爬虫，输出 CSV
- `crawler_pipeline.py` — v2 Selenium 全自动流水线
- `crawler_server.py` — v3 Requests/BS4 版本
- `test_guiji_embedding.py` — 硅基流动 API 一次性验证
- `main.py` — 空壳占位符 ("Hello from vibecheck!")

### 已删除 — deploy_crawler/ (一次性工具和迁移)
- `data_cleaning.py` — 已执行的批量歌词清洗
- `delete_invalid_songs.py` — 已执行的无效数据清除
- `view.sql` — 表结构快照 (与 db_init.py 重复)
- `migrate_v6_core_lyrics.py` — 已应用的 ALTER TABLE
- `migrate/migrate_add_column.py` — 已应用 (is_duplicate)
- `migrate/migrate_v2_vibe_fields.py` — 已应用 (vibe_tags/scores/scene)
- `migrate/migrate_v3_updated_at.py` — 已应用 (updated_at)
- `migrate/migrate_v4_rational_fields.py` — 已应用 (segmented_lyrics/tfidf/review_vector)
- `migrate/migrate_v5_add_comments.py` — 已应用 (列注释)

---

## 六、当前项目结构 (清理后)

```
VibeCheck/
├── .env                          # 环境变量 (API Keys)
├── pyproject.toml                # Python 项目配置 (uv)
├── db_init.py                    # 根目录 DB 初始化 (本地开发用)
├── PRD.md                        # 原始需求文档
├── product_roadmap.md            # 产品规划书
├── README.md                     # 项目说明
│
└── deploy_crawler/               # 🚀 服务器部署包
    ├── docker-compose.yml        # 容器编排
    ├── Dockerfile                # 爬虫容器镜像
    ├── requirements.txt          # Python 依赖
    ├── db_init.py                # 数据库模型 & 初始化
    ├── app.py                    # 爬虫主程序
    ├── mark_duplicates.py        # 数据去重
    ├── batch_ai_analysis.py      # LLM 批量分析
    ├── batch_vectorization.py    # 评语向量化
    ├── batch_lyrics_vectorization.py  # 歌词向量化
    ├── compute_tfidf.py          # 分词 + TF-IDF
    ├── extract_core_lyrics.py    # 核心歌词提取算法
    ├── batch_update_core_lyrics.py    # 批量提取核心歌词
    ├── hybrid_search_test.py     # 混合搜索原型 (测试/Demo)
    ├── test_famous_core_lyrics.py # 核心歌词提取质量测试
    ├── stopwords.txt             # 停用词表
    ├── daily_ai_analysis.sh      # 定时 AI 分析脚本
    ├── run_extract_background.sh # 后台歌词处理脚本
    └── README.md                 # 部署说明
```
