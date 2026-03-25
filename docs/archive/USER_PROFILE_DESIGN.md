# 用户画像与个性化推荐设计文档

> 版本：v1.0
> 
> 更新时间：2026-03-20

---

## 一、概述

本文档详细说明 VibeCheck 的用户画像构建、行为预测和个性化推荐功能的设计与实现方案。

### 1.1 核心概念

| 概念 | 定义 |
|------|------|
| 用户行为 | 用户与系统的交互动作：点击、播放、收藏、跳过、不喜欢 |
| 用户画像 | 用户音乐偏好的向量表示，用于个性化推荐 |
| 行为预测 | 预测用户对未听过歌曲的反应概率 |
| 个性化推荐 | 结合用户画像调整推荐结果 |

### 1.2 整体流程

```
用户行为 → 行为记录 → 偏好学习 → 用户画像 → 个性化推荐
   │          │           │           │            │
 点击/播放    日志存储    更新向量    偏好表示     调整推荐结果
 收藏/跳过
```

---

## 二、用户行为收集

### 2.1 行为类型与权重

| 行为类型 | 权重 | 含义 | 触发时机 |
|----------|------|------|----------|
| `like` | +1.0 | 强烈喜欢 | 用户点击收藏按钮 |
| `play_full` | +0.5 | 喜欢 | 播放时长 > 80% 歌曲时长 |
| `play_half` | +0.3 | 有点兴趣 | 播放时长 30%-80% |
| `click` | +0.2 | 稍有兴趣 | 点击查看歌曲详情 |
| `skip` | -0.3 | 不感兴趣 | 播放时长 < 30% 就切歌 |
| `dislike` | -0.8 | 强烈排斥 | 用户点击不喜欢按钮 |

### 2.2 数据库设计

```sql
-- 用户表
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    last_active_at TIMESTAMP
);

-- 用户行为日志表
CREATE TABLE user_actions (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id),
    song_id VARCHAR(50) NOT NULL REFERENCES songs(id),
    action VARCHAR(20) NOT NULL,  -- 'like', 'play', 'skip', 'dislike'
    duration INTEGER,              -- 播放时长（秒），仅 play 行为有效
    song_duration INTEGER,         -- 歌曲总时长（秒），用于计算播放比例
    created_at TIMESTAMP DEFAULT NOW()
);

-- 索引优化
CREATE INDEX idx_user_actions_user_id ON user_actions(user_id);
CREATE INDEX idx_user_actions_song_id ON user_actions(song_id);
CREATE INDEX idx_user_actions_created_at ON user_actions(created_at);

-- 用户画像表
CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(user_id),
    preference_vector VECTOR(1024),  -- 用户偏好向量（与歌曲向量维度一致）
    vibe_preferences JSONB,          -- 氛围偏好统计 {"治愈": 0.8, "伤感": 0.3}
    artist_preferences JSONB,        -- 歌手偏好统计
    action_count INTEGER DEFAULT 0,  -- 行为总数
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2.3 API 接口设计

```python
# POST /api/user/action
# 记录用户行为

Request:
{
    "user_id": "uuid",
    "song_id": "song_123",
    "action": "play",
    "duration": 120,      # 播放时长（秒）
    "song_duration": 180  # 歌曲总时长（秒）
}

Response:
{
    "status": "ok",
    "action_type": "play_full"  # 实际识别的行为类型
}
```

---

## 三、用户画像构建

### 3.1 核心思想

**用户画像 = 用户喜欢的歌曲向量的加权平均**

```
用户喜欢的歌：伤感、抒情、周杰伦、林俊杰...
        ↓
用户画像向量：[0.2, -0.5, 0.8, 0.1, ...] (1024维)
        ↓
用来和歌曲向量做相似度计算
```

### 3.2 画像构建算法

```python
import numpy as np
from typing import List, Dict
from sqlalchemy import select
from database import get_db

class UserProfileBuilder:
    """用户画像构建器"""
    
    # 行为权重映射
    ACTION_WEIGHTS = {
        'like': 1.0,
        'play_full': 0.5,
        'play_half': 0.3,
        'click': 0.2,
        'skip': -0.3,
        'dislike': -0.8,
    }
    
    def classify_play_action(self, duration: int, song_duration: int) -> str:
        """根据播放时长分类播放行为"""
        if duration is None or song_duration is None:
            return 'play_half'
        
        ratio = duration / song_duration
        if ratio > 0.8:
            return 'play_full'
        elif ratio > 0.3:
            return 'play_half'
        else:
            return 'skip'
    
    async def get_user_actions(self, user_id: str) -> List[Dict]:
        """获取用户所有行为记录"""
        async with get_db() as db:
            result = await db.execute("""
                SELECT ua.song_id, ua.action, ua.duration, ua.song_duration
                FROM user_actions ua
                WHERE ua.user_id = $1
                ORDER BY ua.created_at DESC
                LIMIT 1000  -- 限制最近1000条行为
            """, user_id)
            return result.fetchall()
    
    async def get_song_embedding(self, song_id: str) -> np.ndarray:
        """获取歌曲的语义向量"""
        async with get_db() as db:
            result = await db.execute("""
                SELECT review_vector FROM songs WHERE id = $1
            """, song_id)
            row = result.fetchone()
            if row and row['review_vector']:
                return np.array(row['review_vector'])
            return None
    
    async def build_profile(self, user_id: str) -> np.ndarray:
        """构建用户画像向量"""
        
        # 1. 获取用户所有行为记录
        actions = await self.get_user_actions(user_id)
        
        if not actions:
            # 新用户：返回零向量
            return np.zeros(1024)
        
        # 2. 加权聚合
        weighted_sum = np.zeros(1024)
        total_weight = 0
        
        for action in actions:
            song_embedding = await self.get_song_embedding(action['song_id'])
            if song_embedding is None:
                continue
            
            # 确定行为类型
            if action['action'] == 'play':
                action_type = self.classify_play_action(
                    action['duration'], 
                    action['song_duration']
                )
            else:
                action_type = action['action']
            
            weight = self.ACTION_WEIGHTS.get(action_type, 0)
            
            weighted_sum += weight * song_embedding
            total_weight += abs(weight)
        
        # 3. 归一化
        if total_weight > 0:
            profile = weighted_sum / total_weight
            # L2 归一化，使向量长度为1
            norm = np.linalg.norm(profile)
            if norm > 0:
                profile = profile / norm
        else:
            profile = np.zeros(1024)
        
        return profile
    
    async def save_profile(self, user_id: str, profile: np.ndarray):
        """保存用户画像到数据库"""
        async with get_db() as db:
            await db.execute("""
                INSERT INTO user_profiles (user_id, preference_vector, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    preference_vector = $2,
                    updated_at = NOW()
            """, user_id, profile.tolist())
```

### 3.3 增量更新策略

为避免每次都全量重算，采用增量更新：

```python
class ProfileUpdater:
    """用户画像增量更新器"""
    
    async def update_on_action(self, user_id: str, song_id: str, action: str, 
                                 duration: int = None, song_duration: int = None):
        """用户行为触发增量更新"""
        
        # 1. 获取歌曲向量
        song_embedding = await self.get_song_embedding(song_id)
        if song_embedding is None:
            return
        
        # 2. 计算行为权重
        if action == 'play':
            action_type = self.classify_play_action(duration, song_duration)
        else:
            action_type = action
        weight = ACTION_WEIGHTS.get(action_type, 0)
        
        # 3. 获取当前画像
        current_profile = await self.get_user_profile(user_id)
        
        if current_profile is None:
            # 新用户，直接初始化
            new_profile = weight * song_embedding
        else:
            # 增量更新公式
            # new = (1-α) * old + α * weight * song_embedding
            # α = 学习率，控制新行为的影响程度
            alpha = 0.1
            new_profile = (1 - alpha) * current_profile + alpha * weight * song_embedding
        
        # 4. 归一化
        norm = np.linalg.norm(new_profile)
        if norm > 0:
            new_profile = new_profile / norm
        
        # 5. 保存
        await self.save_profile(user_id, new_profile)
        
        # 6. 更新氛围偏好统计
        await self.update_vibe_preferences(user_id, song_id, action_type)
```

---

## 四、行为预测

### 4.1 预测目标

预测用户对一首**未听过的歌**可能产生的行为：

| 预测项 | 含义 | 用途 |
|--------|------|------|
| `like_prob` | 收藏概率 | 高概率歌曲优先推荐 |
| `play_prob` | 播放概率 | 主要推荐指标 |
| `skip_prob` | 跳过概率 | 低概率歌曲降权 |

### 4.2 预测模型

```python
class BehaviorPredictor:
    """用户行为预测器"""
    
    def __init__(self):
        # 预测阈值配置
        self.like_threshold = 0.6
        self.skip_threshold = 0.4
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)
    
    def predict(self, user_profile: np.ndarray, song_embedding: np.ndarray) -> Dict:
        """预测用户对这首歌的行为概率"""
        
        # 计算相似度（核心特征）
        similarity = self.cosine_similarity(user_profile, song_embedding)
        
        # 相似度范围 [-1, 1]，映射到行为概率
        # 使用 sigmoid 函数平滑映射
        return {
            'similarity': float(similarity),
            'like_prob': self._sigmoid(3 * similarity - 0.3),
            'play_prob': self._sigmoid(2 * similarity),
            'skip_prob': self._sigmoid(-2 * similarity + 0.3),
        }
    
    def _sigmoid(self, x: float) -> float:
        """Sigmoid 函数"""
        return 1 / (1 + np.exp(-max(-10, min(10, x))))
    
    def predict_with_features(self, user_profile: np.ndarray, song: dict) -> float:
        """综合预测用户参与度得分"""
        
        # 1. 语义匹配度
        semantic_sim = self.cosine_similarity(user_profile, song['embedding'])
        
        # 2. 氛围匹配度（如果歌曲有氛围标签）
        vibe_match = 0.5  # 默认中性
        if song.get('vibe_tags'):
            # TODO: 与用户偏好氛围匹配
            pass
        
        # 3. 热度因子
        popularity = np.log1p(song.get('play_count', 0)) / 10
        
        # 4. 新鲜度因子
        # TODO: 根据发行日期计算
        
        # 综合得分
        score = (
            0.5 * semantic_sim +
            0.2 * vibe_match +
            0.2 * popularity +
            0.1 * 0.5  # 新鲜度默认值
        )
        
        return score
```

---

## 五、个性化推荐

### 5.1 推荐流程

```
用户输入查询
      │
      ▼
┌─────────────┐
│ 意图理解    │  用户输入 → 语义向量
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 获取画像    │  从数据库读取用户偏好向量
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 向量融合    │  α * 查询向量 + (1-α) * 用户画像
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 向量召回    │  pgvector 检索 Top-100
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 过滤去重    │  排除已听过的歌
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 精排打分    │  多目标预测 + 加权排序
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 多样性控制  │  歌手去重、氛围打散
└──────┬──────┘
       │
       ▼
   返回结果
```

### 5.2 核心代码实现

```python
from typing import List, Optional
import numpy as np

class PersonalizedRecommender:
    """个性化推荐器"""
    
    def __init__(self, alpha: float = 0.7):
        """
        Args:
            alpha: 个性化权重，0-1之间
                   1.0 = 完全听用户的查询意图
                   0.0 = 完全根据用户历史偏好
        """
        self.alpha = alpha
        self.behavior_predictor = BehaviorPredictor()
    
    async def recommend(self, user_id: str, query: str, k: int = 20) -> List[dict]:
        """个性化推荐主入口"""
        
        # Step 1: 意图理解
        query_embedding = await self.encode_query(query)
        
        # Step 2: 获取用户画像
        user_profile = await self.get_user_profile(user_id)
        
        # Step 3: 向量融合
        if user_profile is not None and np.linalg.norm(user_profile) > 0:
            search_vector = self.blend_vectors(query_embedding, user_profile)
        else:
            # 新用户，只用查询向量
            search_vector = query_embedding
        
        # Step 4: 向量召回
        candidates = await self.vector_search(search_vector, top_k=100)
        
        # Step 5: 过滤已听过的歌
        heard_songs = await self.get_user_heard_songs(user_id)
        candidates = [c for c in candidates if c['id'] not in heard_songs]
        
        # Step 6: 精排打分（如果有用户画像）
        if user_profile is not None:
            candidates = self.rank_with_personalization(candidates, user_profile)
        
        # Step 7: 多样性控制
        candidates = self.diversify(candidates)
        
        # Step 8: Top-K 选择
        return candidates[:k]
    
    def blend_vectors(self, query_vec: np.ndarray, profile_vec: np.ndarray) -> np.ndarray:
        """融合查询意图和用户偏好"""
        blended = self.alpha * query_vec + (1 - self.alpha) * profile_vec
        # 归一化
        norm = np.linalg.norm(blended)
        if norm > 0:
            blended = blended / norm
        return blended
    
    def rank_with_personalization(self, candidates: List[dict], 
                                   user_profile: np.ndarray) -> List[dict]:
        """个性化精排"""
        for candidate in candidates:
            song_embedding = np.array(candidate['review_vector'])
            
            # 预测用户行为
            prediction = self.behavior_predictor.predict(user_profile, song_embedding)
            
            # 综合得分 = 语义相似度 * 0.5 + 预测播放概率 * 0.3 - 预测跳过概率 * 0.2
            score = (
                0.5 * candidate['similarity'] +
                0.3 * prediction['play_prob'] -
                0.2 * prediction['skip_prob']
            )
            
            candidate['personalized_score'] = score
            candidate['prediction'] = prediction
        
        # 按综合得分排序
        return sorted(candidates, key=lambda x: x['personalized_score'], reverse=True)
    
    def diversify(self, candidates: List[dict], 
                  max_same_artist: int = 2) -> List[dict]:
        """多样性控制：限制同一歌手的歌曲数量"""
        result = []
        artist_counts = {}
        
        for candidate in candidates:
            artist = candidate.get('artist', 'unknown')
            count = artist_counts.get(artist, 0)
            
            if count < max_same_artist:
                result.append(candidate)
                artist_counts[artist] = count + 1
        
        return result
```

---

## 六、氛围偏好统计

除了向量画像，还可以统计用户的氛围偏好分布：

```sql
-- 用户氛围偏好表
CREATE TABLE user_vibe_preferences (
    user_id UUID REFERENCES users(user_id),
    vibe_tag VARCHAR(50),
    score FLOAT DEFAULT 0,       -- 偏好得分
    action_count INTEGER DEFAULT 0,  -- 相关行为次数
    updated_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, vibe_tag)
);
```

```python
class VibePreferenceTracker:
    """氛围偏好追踪器"""
    
    async def update_vibe_preference(self, user_id: str, song_id: str, action: str):
        """更新用户对某氛围的偏好"""
        
        # 1. 获取歌曲的氛围标签
        async with get_db() as db:
            result = await db.execute("""
                SELECT vibe_tags FROM songs WHERE id = $1
            """, song_id)
            row = result.fetchone()
        
        if not row or not row['vibe_tags']:
            return
        
        vibe_tags = row['vibe_tags']
        
        # 2. 计算行为对氛围的影响
        weight = ACTION_WEIGHTS.get(action, 0)
        
        # 3. 更新每个氛围的偏好得分
        async with get_db() as db:
            for vibe in vibe_tags:
                await db.execute("""
                    INSERT INTO user_vibe_preferences (user_id, vibe_tag, score, action_count)
                    VALUES ($1, $2, $3, 1)
                    ON CONFLICT (user_id, vibe_tag)
                    DO UPDATE SET
                        score = user_vibe_preferences.score + $3,
                        action_count = user_vibe_preferences.action_count + 1,
                        updated_at = NOW()
                """, user_id, vibe, weight)
    
    async def get_top_vibes(self, user_id: str, limit: int = 10) -> List[dict]:
        """获取用户最喜欢的氛围"""
        async with get_db() as db:
            result = await db.execute("""
                SELECT vibe_tag, score, action_count
                FROM user_vibe_preferences
                WHERE user_id = $1 AND score > 0
                ORDER BY score DESC
                LIMIT $2
            """, user_id, limit)
            return result.fetchall()
```

---

## 七、API 接口完整设计

### 7.1 用户行为接口

```
POST /api/user/action
记录用户行为

Request:
{
    "user_id": "uuid",
    "song_id": "song_123",
    "action": "like",      // like, play, skip, dislike
    "duration": 120,       // 仅 play 需要
    "song_duration": 180   // 仅 play 需要
}

Response:
{
    "status": "ok",
    "action_type": "like",
    "profile_updated": true
}
```

### 7.2 个性化推荐接口

```
POST /api/recommend/personalized
个性化推荐

Request:
{
    "user_id": "uuid",
    "query": "想听一首悲伤的歌",
    "k": 20,
    "alpha": 0.7  // 可选，个性化权重
}

Response:
{
    "songs": [
        {
            "id": "song_123",
            "title": "晴天",
            "artist": "周杰伦",
            "similarity": 0.85,
            "personalized_score": 0.72,
            "prediction": {
                "like_prob": 0.65,
                "play_prob": 0.78,
                "skip_prob": 0.12
            }
        },
        ...
    ],
    "user_profile_exists": true
}
```

### 7.3 用户画像接口

```
GET /api/user/{user_id}/profile
获取用户画像

Response:
{
    "user_id": "uuid",
    "action_count": 128,
    "top_vibes": [
        {"vibe": "伤感", "score": 15.2},
        {"vibe": "治愈", "score": 12.8},
        ...
    ],
    "top_artists": [
        {"artist": "周杰伦", "count": 23},
        ...
    ],
    "created_at": "2026-03-01T00:00:00Z",
    "updated_at": "2026-03-20T00:00:00Z"
}
```

---

## 八、实现检查清单

### 数据库层
- [ ] 创建 `users` 表
- [ ] 创建 `user_actions` 表
- [ ] 创建 `user_profiles` 表
- [ ] 创建 `user_vibe_preferences` 表
- [ ] 创建相关索引

### 后端服务层
- [ ] 实现 `POST /api/user/action` 接口
- [ ] 实现 `UserProfileBuilder` 类
- [ ] 实现 `ProfileUpdater` 增量更新
- [ ] 实现 `BehaviorPredictor` 预测器
- [ ] 实现 `PersonalizedRecommender` 推荐器
- [ ] 实现 `VibePreferenceTracker` 氛围追踪

### 前端交互层
- [ ] 用户行为埋点（播放、收藏、跳过）
- [ ] 个性化推荐结果展示
- [ ] 用户画像页面（可选）

---

## 九、参考资料

1. xAI. x-algorithm: Algorithm powering the For You feed on X. GitHub, 2024.
2. Pazzani M J, Billsus D. Content-based recommendation systems. Springer, 2007.
3. Covington P, Adams J, Sargin E. Deep neural networks for YouTube recommendations. RecSys, 2016.