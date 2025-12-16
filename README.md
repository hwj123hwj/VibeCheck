# VibeCheck - 混合音乐推荐系统

VibeCheck 是一个基于 **AI 情感分析** 和 **混合检索** (TF-IDF + Vector Embedding) 的音乐推荐系统。它不仅推荐相似风格的歌曲，还能通过大模型生成“网抑云”风格的情感评语。

## 🌟 核心功能

1.  **多模态数据采集**: 爬取网易云音乐热门歌单、歌曲元数据及歌词。
2.  **混合特征工程**:
    *   **TF-IDF**: 基于歌词关键词的稀疏向量检索。
    *   **Vector Embedding**: 使用 `BAAI/bge-m3` 模型对 LLM 生成的情感评语进行向量化。
3.  **智能推荐算法**: 结合稀疏检索和向量检索的混合推荐逻辑。
4.  **AI 情感伴侣**: 使用 LLM (LongMao) 为每首歌曲生成独特的情感短评。

## 🛠️ 技术栈

*   **语言**: Python 3.12
*   **依赖管理**: `uv`
*   **Web 框架**: FastAPI
*   **数据库**: PostgreSQL + `pgvector` 插件
*   **爬虫**: Requests, BeautifulSoup (Server-ready)
*   **前端**: React + Vite + Tailwind CSS (计划中)

## 📂 项目结构

```
d:\competition\VibeCheck
├── deploy_crawler/       # 🚀 服务器部署包 (Docker)
│   ├── app.py            # 服务端爬虫主程序
│   ├── docker-compose.yml# 一键部署配置
│   └── ...
├── data/                 # 本地数据存储 (CSV)
├── step1_get_playlists.py# [本地开发] 爬取歌单
├── step2_get_songs.py    # [本地开发] 爬取歌曲
├── step3_get_lyrics.py   # [本地开发] 爬取歌词
├── db_init.py            # 数据库初始化脚本
└── PRD.md                # 需求文档
```

## 🚀 快速开始 (服务器部署)

我们提供了一套完整的 Docker 部署方案，适合在 Linux 服务器上长期运行数据采集任务。

1.  **上传代码**: 将 `deploy_crawler` 文件夹上传至服务器。
2.  **启动服务**:
    ```bash
    cd deploy_crawler
    docker-compose up --build -d
    ```
3.  **自动运行**:
    *   PostgreSQL 数据库将在端口 `5433` 启动。
    *   爬虫程序将自动开始抓取 54 页热门歌单 (约 1890 个)，并实时存入数据库。

## 💻 本地开发

1.  **环境配置**:
    ```bash
    uv init
    uv sync
    ```
2.  **启动数据库**:
    确保本地安装了 Docker Desktop，运行 `deploy_crawler` 中的 `docker-compose.yml` 启动数据库服务。
3.  **运行分步爬虫**:
    ```bash
    uv run step1_get_playlists.py
    uv run step2_get_songs.py
    uv run step3_get_lyrics.py
    ```

## 📝 许可证

MIT License
