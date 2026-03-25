# 系统架构设计文档

> 版本：v1.0
> 
> 更新时间：2026-03-20

---

## 一、整体架构

### 1.1 架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                          用户交互层                                   │
│    Web 前端 (React) / 移动端 / API 接口                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          服务网关层                                   │
│    Nginx 反向代理 / 负载均衡 / 统一鉴权                                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          业务服务层                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │ 用户服务     │  │ 推荐服务     │  │ 内容服务     │                  │
│  │ UserService │  │ RecService  │  │ContentSvc   │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
│                                                                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │ 搜索服务     │  │ 排序服务     │  │ 特征服务     │                  │
│  │SearchService│  │RankService  │  │FeatureSvc   │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          数据存储层                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                  │
│  │ PostgreSQL  │  │   Redis     │  │  pgvector   │                  │
│  │ 主数据存储   │  │ 缓存/会话   │  │ 向量检索     │                  │
│  └─────────────┘  └─────────────┘  └─────────────┘                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          离线计算层                                   │
│  特征工程 / 向量预计算 / 用户画像更新 / 定时任务调度                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 核心设计原则

| 原则 | 说明 |
|------|------|
| 语义优先 | 采用 LLM embedding 替代传统 TF-IDF，实现深层次语义理解 |
| 模块解耦 | 各服务独立部署，通过 API 通信，便于扩展和维护 |
| 可扩展性 | 预留音频特征、协同过滤等模块接口，支持后续功能扩展 |

---

## 二、推荐流程 Pipeline

```
用户请求
    │
    ▼
┌─────────────────┐
│   意图理解       │  用户输入 → 语义向量
│  Intent Parser  │  "想听一首悲伤的歌" → embedding
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   候选召回       │  向量相似度检索，召回 Top-100
│   Retrieval     │  pgvector 余弦相似度
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   特征补充       │  补充歌曲元信息
│   Hydration     │  歌手、专辑、热度、氛围标签
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   过滤筛选       │  去重、过滤已听、排除不喜欢歌手
│   Filtering     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   精排打分       │  多目标预测 + 个性化加权
│   Ranking       │  Score = α×语义相似度 + β×用户偏好
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   多样性控制     │  歌手去重、氛围打散
│   Diversity     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   结果选择       │  Top-K 选择
│   Selection     │
└─────────────────┘
         │
         ▼
    返回推荐结果
```

---

## 三、召回模块设计

### 3.1 双塔模型架构

参考 X 的 Phoenix 架构，采用**双塔模型**（Two-Tower Model）进行语义召回：

```
┌───────────────────────────────────────────────────────────────┐
│                        双塔模型                                 │
│                                                                │
│   ┌─────────────────┐              ┌─────────────────┐        │
│   │   Query Tower   │              │ Candidate Tower │        │
│   │   (用户塔)       │              │  (物品塔)        │        │
│   │                 │              │                 │        │
│   │ 用户输入文本     │              │ 歌词/评语        │        │
│   │      │          │              │      │          │        │
│   │      ▼          │              │      ▼          │        │
│   │   LLM Encoder   │              │   LLM Encoder   │        │
│   │      │          │              │      │          │        │
│   │      ▼          │              │      ▼          │        │
│   │  Query Vector   │              │ Item Vector     │        │
│   │   (1024维)      │              │  (1024维)       │        │
│   └────────┬────────┘              └────────┬────────┘        │
│            │                                │                  │
│            └────────────┬───────────────────┘                  │
│                         │                                      │
│                         ▼                                      │
│              ┌─────────────────┐                               │
│              │  余弦相似度计算   │                               │
│              │  cos(q, i) =    │                               │
│              │  q·i / |q||i|   │                               │
│              └─────────────────┘                               │
│                                                                │
└───────────────────────────────────────────────────────────────┘
```

### 3.2 语义特征提取

```python
from openai import OpenAI
import numpy as np

client = OpenAI(base_url="https://api.siliconflow.cn/v1")

def get_embedding(text: str) -> np.ndarray:
    """使用 LLM 生成文本语义向量"""
    response = client.embeddings.create(
        model="BAAI/bge-large-zh-v1.5",
        input=text
    )
    return np.array(response.data[0].embedding)
```

### 3.3 向量检索

```sql
-- 创建向量索引（IVFFlat 适合中等规模数据）
CREATE INDEX ON songs USING ivfflat (review_vector vector_cosine_ops) 
WITH (lists = 100);

-- 向量检索查询
SELECT id, title, artist, 
       1 - (review_vector <=> query_vector) as similarity
FROM songs
ORDER BY review_vector <=> query_vector
LIMIT 100;
```

---

## 四、排序模块设计

### 4.1 多目标预测

预测用户对歌曲的多种行为概率：

```python
class MultiObjectiveScorer:
    """多目标预测器"""
    
    def __init__(self):
        self.weights = {
            'semantic_similarity': 0.4,
            'user_preference': 0.3,
            'popularity': 0.15,
            'recency': 0.15,
        }
    
    def compute_score(self, candidate: dict, user_profile: dict) -> float:
        scores = {
            'semantic_similarity': candidate['similarity'],
            'user_preference': self._preference_match(candidate, user_profile),
            'popularity': self._normalize_popularity(candidate['play_count']),
            'recency': self._recency_score(candidate['release_date']),
        }
        return sum(self.weights[k] * v for k, v in scores.items())
```

### 4.2 综合评分函数

$$
S_i = \alpha \cdot \text{sim}(\mathbf{q}, \mathbf{e}_i) + \beta \cdot \text{sim}(\mathbf{p}_u, \mathbf{e}_i) + \gamma \cdot \phi(i)
$$

其中：
- $\mathbf{q}$ 为用户查询意图向量
- $\mathbf{e}_i$ 为歌曲 $i$ 的语义向量
- $\mathbf{p}_u$ 为用户 $u$ 的偏好向量
- $\phi(i)$ 为歌曲 $i$ 的热度/新鲜度因子
- $\alpha, \beta, \gamma$ 为可调权重参数

### 4.3 参数设置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| $\alpha$ | 0.5 | 查询意图权重 |
| $\beta$ | 0.3 | 用户偏好权重 |
| $\gamma$ | 0.2 | 热度因子权重 |

---

## 五、多样性控制

### 5.1 歌手多样性

```python
class ArtistDiversityScorer:
    """歌手多样性控制"""
    
    def __init__(self, decay_factor: float = 0.85):
        self.decay_factor = decay_factor
    
    def diversify(self, candidates: list, max_same: int = 2) -> list:
        """限制同一歌手的歌曲数量"""
        result = []
        artist_counts = {}
        
        for candidate in candidates:
            artist = candidate['artist']
            count = artist_counts.get(artist, 0)
            
            if count < max_same:
                result.append(candidate)
                artist_counts[artist] = count + 1
        
        return result
```

### 5.2 氛围多样性

```python
class VibeDiversityScorer:
    """氛围多样性控制"""
    
    def diversify(self, candidates: list, max_same_vibe: int = 3) -> list:
        """限制相同氛围歌曲连续出现"""
        result = []
        vibe_counts = {}
        
        for candidate in candidates:
            vibe = candidate.get('vibe', 'unknown')
            count = vibe_counts.get(vibe, 0)
            
            if count < max_same_vibe:
                result.append(candidate)
                vibe_counts[vibe] = count + 1
        
        return result
```

---

## 六、技术选型

| 层次 | 技术栈 | 说明 |
|------|--------|------|
| 前端 | React + TypeScript + Tailwind CSS | 响应式 UI |
| 后端 | Python + FastAPI | 高性能异步 API |
| 数据库 | PostgreSQL + pgvector | 关系数据 + 向量检索 |
| 缓存 | Redis | 热点数据缓存 |
| Embedding | SiliconFlow (BGE-large-zh) | 中文语义理解 |

---

## 七、数据模型

```sql
-- 歌曲表
CREATE TABLE songs (
    id VARCHAR(50) PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    artist VARCHAR(100) NOT NULL,
    album VARCHAR(200),
    lyrics TEXT,
    review_text TEXT,
    review_vector VECTOR(1024),
    core_lyrics TEXT,
    lyrics_vector VECTOR(1024),
    vibe_tags TEXT[],
    tfidf_keywords JSONB,
    play_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 用户表
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 用户行为日志
CREATE TABLE user_actions (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    song_id VARCHAR(50) REFERENCES songs(id),
    action VARCHAR(20),
    duration INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 用户画像
CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(user_id),
    preference_vector VECTOR(1024),
    vibe_preferences JSONB,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 八、扩展路线图

### v1.0 当前版本
- [x] 语义向量召回
- [x] 基础排序
- [x] 前后端联调

### v1.1 近期扩展
- [ ] 用户画像 + 偏好学习
- [ ] 多样性控制
- [ ] Redis 缓存层

### v2.0 中期扩展
- [ ] 音频特征提取（librosa）
- [ ] 多维度融合（文本 + 音频）
- [ ] A/B 测试框架

### v3.0 远期扩展
- [ ] 协同过滤
- [ ] 实时推荐（Kafka）
- [ ] 深度排序模型

---

## 九、参考文献

1. xAI. x-algorithm: Algorithm powering the For You feed on X. GitHub, 2024.
2. Pazzani M J, Billsus D. Content-based recommendation systems. Springer, 2007.
3. Balabanović M, Shoham Y. Content-based, collaborative recommendation. CACM, 1997.
4. Van den Oord A, et al. Deep content-based music recommendation. NIPS, 2013.