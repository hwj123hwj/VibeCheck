我是开发者，这是我的毕业设计 PRD。请仔细阅读，并根据这份文档帮我初始化项目并逐步实现。

# 🎵 毕业设计 PRD：基于 LLM 语义评语与 TF-IDF 的混合音乐推荐系统

## 1. 项目概述 (Project Overview)
本项目旨在构建一个华语流行音乐推荐系统。系统通过融合**“理性特征”（基于歌词文本的 TF-IDF 关键词）和“感性特征”**（基于大模型生成的语义评语 Embedding），解决传统推荐系统难以捕捉歌曲深层情感意境的问题。

**核心创新点：**
放弃传统的“情感打分（0-1分类）”，采用 **Generative Semantic Representation（生成式语义表征）**。即利用 LLM 阅读歌词生成一段“专业乐评”，再将乐评通过 API 转化为向量进行相似度计算。

## 2. 技术栈架构 (Tech Stack)
* **开发环境**：Python 3.12
* **数据库**：PostgreSQL (需安装 pgvector 插件)
* **后端框架**：FastAPI
* **前端框架**：React + Vite + Tailwind CSS
* **核心算法库**：
    * 爬虫：Selenium, Requests
    * NLP处理：Jieba (分词), Scikit-learn (TF-IDF)
    * **大模型调用 (LLM)**：LongMao (LongCat-Flash-Chat) - 兼容 OpenAI SDK
    * **向量化 (Embedding)**：硅基流动 API (BAAI/bge-m3)

## 3. 数据库设计 (Database Schema)
请在 PostgreSQL 中创建一个名为 `music_db` 的数据库。
**注意：BAAI/bge-m3 模型的输出维度为 1024，请务必设置正确的向量维度。**

| 表名：songs | | |
| :--- | :--- | :--- |
| **字段名** | **类型** | **说明** |
| `id` | VARCHAR(50) | 主键，网易云音乐 Song ID |
| `title` | VARCHAR(255) | 歌曲标题 |
| `artist` | VARCHAR(255) | 歌手名 |
| `lyrics` | TEXT | 原始歌词（已清洗时间轴） |
| `segmented_lyrics` | TEXT | 分词后的歌词（空格分隔，用于 TF-IDF） |
| `review_text` | TEXT | **[核心]** LLM 生成的情感评语 |
| `review_vector` | VECTOR(1024) | **[核心]** 评语的 Embedding 向量 (注意维度是 1024) |
| `tfidf_vector` | JSONB | TF-IDF 向量 (稀疏向量，存为 JSON 索引或数组) |
| `album_cover` | VARCHAR(500) | (可选) 专辑封面图片 URL |
| `created_at` | TIMESTAMP | 入库时间 |

## 4. 详细实现流程 (Implementation Roadmap)

### 阶段一：数据工程 (Data Engineering)
**任务 1.1：爬虫脚本 (`crawler.py`)**
* **目标**：抓取网易云音乐“热歌榜” Top 200 数据。
* **逻辑**：
    1.  使用 Selenium 打开 `https://music.163.com/#/discover/toplist?id=3778678`。
    2.  切换 iframe，获取歌曲列表（ID, 标题, 歌手）。
    3.  遍历歌曲 ID，使用 Requests 调用 API `http://music.163.com/api/song/lyric?id={id}&lv=1` 获取歌词。
* **数据清洗**：
    1.  正则去除时间轴 `[00:00.00]`。
    2.  正则去除元数据（如 `作词 : xxx`）。
    3.  保留纯净歌词文本，存入数据库。

### 阶段二：特征工程 (Feature Engineering) —— 核心算法层
**任务 2.1：理性特征提取 (`process_tfidf.py`)**
* 读取 `lyrics`，加载停用词表，使用 Jieba 分词更新 `segmented_lyrics`。
* 使用 `TfidfVectorizer (max_features=100)` 计算矩阵并存入 `tfidf_vector`。

**任务 2.2：感性特征生成 (`process_emotion_llm.py`)**
* **步骤 A：LLM 生成评语 (调用 LongMao)**
    * **Base URL**: `https://api.longcat.chat/openai`
    * **Model**: `LongCat-Flash-Chat`
    * **Prompt**:
        ```text
        你是一位专业的音乐推荐算法辅助员。请分析歌曲《{title}》的歌词。
        ---
        {lyrics}
        ---
        请生成一段 **60字左右** 的侧写评语，用于生成向量特征。
        【关键要求】
        1. 捕捉情感基调：是“明快的”还是“沉郁的”？是“温暖的”还是“冰冷的”？
        2. 具体场景：如果有具体意象（如校园、海边、派对），请明确写出。
        3. 拒绝矫情：不要堆砌空洞的大词，用具体的词描述，如“失恋后的自省”、“热恋时的甜蜜”。
        4. 格式：直接输出评语文本，不要包含任何前缀。
        ```
    * 将结果存入 `review_text`。

* **步骤 B：向量化 Embedding (调用硅基流动)**
    * **Base URL**: `https://api.siliconflow.cn/v1/embeddings`
    * **Model**: `BAAI/bge-m3`
    * **逻辑**: 将 `review_text` 发送给 API，获取 **1024维** 向量。
    * 存入数据库 `review_vector`。

### 阶段三：推荐算法服务 (Algorithm Service)
**任务 3.1：混合推荐逻辑 (`recommender.py`)**
* 输入：`target_song_id`
* 计算相似度：
    * $Sim_{text} = CosineSimilarity(vec\_text\_A, vec\_text\_B)$
    * $Sim_{emo} = CosineSimilarity(vec\_emo\_A, vec\_emo\_B)$ (基于 1024维向量)
* 加权融合：
    * $FinalScore = 0.3 \cdot Sim_{text} + 0.7 \cdot Sim_{emo}$
* 排序：返回 Score 最高的 Top 10。

### 阶段四：全栈应用开发 (Web Application)
* **后端 (`main.py`)**: FastAPI 提供 `/api/recommend/{id}` 等接口。
* **前端 (React)**: 首页瀑布流 + 详情页（展示高亮 AI 评语）。

---

## 5. 给 AI IDE 的指令清单 (Prompts for Cursor/Windsurf)
请按以下步骤帮我生成代码：

**Step 1 (环境与数据库):**
"请帮我创建 `requirements.txt`，Python 版本 3.12。需要包含：`fastapi`, `uvicorn`, `sqlalchemy`, `psycopg2-binary`, `pgvector`, `selenium`, `requests`, `jieba`, `scikit-learn`, `openai` (用于调用兼容接口)。
然后编写 `db_init.py`，连接本地 PostgreSQL，创建 songs 表。**特别注意：review_vector 字段必须定义为 VECTOR(1024) 以匹配 bge-m3 模型。**"

**Step 2 (爬虫):**
"编写 `crawler.py`。使用 Selenium 无头模式抓取网易云热歌榜，清洗歌词后存入数据库。确保处理好异常和等待。"

**Step 3 (核心特征处理 - API调用):**
"编写 `process_features.py`。
1. **TF-IDF**: 读取歌词，Jieba 分词，计算 TF-IDF 存入 JSON 字段。
2. **LLM 生成**: 使用 `openai` 库调用 **LongMao** (Base URL: `https://api.longcat.chat/openai`, Model: `LongCat-Flash-Chat`) 生成评语。
3. **Embedding**: 使用 `requests` 或 `openai` 库调用 **硅基流动** (URL: `https://api.siliconflow.cn/v1/embeddings`, Model: `BAAI/bge-m3`) 将评语转为 1024维向量。
4. 更新数据库，支持断点续传。"

**Step 4 (推荐接口):**
"编写 FastAPI `main.py`。实现 `get_recommendations(song_id)`。从 DB 读取 1024维向量和 TF-IDF 向量，计算加权余弦相似度 (0.3/0.7)，返回 Top 10。"

**Step 5 (前端):**
"初始化 React + Vite 项目。实现首页列表和详情页。详情页要重点展示 'AI 情感评语' 和推荐列表。"