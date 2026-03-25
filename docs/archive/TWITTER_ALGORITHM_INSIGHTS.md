# Twitter 推荐算法对 VibeCheck 的启发

> **分析对象**：X Algorithm (Twitter Recommendation System)  
> **日期**：2026-02-11

---

## Twitter 算法核心架构

```
Query (用户请求)
  ↓
QueryHydrator (补充用户特征)
  ↓
Source (多源候选生成)
  ↓
Hydrator (候选数据水合)
  ↓
Filter (过滤器链)
  ↓
Scorer (多评分器加权)
  ↓
Selector (Top-K 选择)
  ↓
Post-Selection Hydrator & Filter
  ↓
SideEffect (日志/缓存)
  ↓
Result
```

---

## 可借鉴的 5 个关键设计

### 1. 多样性控制 (AuthorDiversityScorer)

**Twitter 的实现**：
```rust
// 同一作者的第 N 首歌，分数衰减
fn multiplier(&self, position: usize) -> f64 {
    (1.0 - floor) * decay_factor.powf(position) + floor
}

// 举例：decay_factor=0.5, floor=0.2
// 第 1 首：1.0
// 第 2 首：0.6  (防止刷屏，但保留一定权重)
// 第 3 首：0.4
```

**对 VibeCheck 的启发**：
- **问题**：搜索"伤感"可能前 10 首全是周杰伦，用户体验单调
- **方案**：在 `search.py` 或前端增加 `ArtistDiversityReranker`
  ```python
  def apply_artist_diversity(results, decay=0.6, floor=0.3):
      artist_count = {}
      for song in results:
          position = artist_count.get(song.artist, 0)
          multiplier = (1 - floor) * (decay ** position) + floor
          song.score *= multiplier
          artist_count[song.artist] = position + 1
      return sorted(results, key=lambda x: x.score, reverse=True)
  ```

---

### 2. 用户级播放历史去重 (PreviouslySeenPostsFilter)

**Twitter 的实现**：
```rust
// 客户端发送已看过的 ID + Bloom Filter
let is_seen = query.seen_ids.contains(&post_id)
    || bloom_filters.iter().any(|f| f.may_contain(post_id));
```

**对 VibeCheck 的启发**：
- **问题**：用户搜索同一关键词时，结果总是一样，缺乏新鲜感
- **方案**：
  1. **前端**：LocalStorage 记录已播放歌曲 ID
     ```javascript
     const playedSongs = JSON.parse(localStorage.getItem('playedSongs') || '[]')
     ```
  2. **后端**：搜索接口接受 `?exclude_ids=123,456,789`
     ```sql
     WHERE id NOT IN (:exclude_ids)
     ```
  3. **进阶**：使用 Redis Bloom Filter 存储用户播放历史（百万级数据，几 KB 空间）

---

### 3. 多评分器组合 (WeightedScorer)

**Twitter 的实现**：
```rust
combined_score = 
    favorite_score * FAVORITE_WEIGHT +
    reply_score * REPLY_WEIGHT +
    retweet_score * RETWEET_WEIGHT +
    click_score * CLICK_WEIGHT +
    dwell_score * DWELL_WEIGHT +
    ...
```

**对 VibeCheck 的启发**：
- **当前**：只有 3 路（review, lyrics, rational）
- **扩展方向**：
  ```python
  # 可以引入更多维度
  final_score = (
      review_score * 0.4 +
      lyrics_score * 0.3 +
      rational_score * 0.1 +
      popularity_score * 0.1 +  # 播放量/收藏量
      recency_score * 0.05 +    # 发行时间（新歌加权）
      user_history_score * 0.05 # 用户听歌风格匹配度
  )
  ```

---

### 4. 管道化架构 (Candidate Pipeline)

**Twitter 的模块分离**：
```
Source (多源) → Hydrator (水合) → Filter (过滤) → Scorer (评分) → Selector (选择)
```

**对 VibeCheck 的启发**：
- **当前**：单一 SQL 一次性完成所有逻辑（5.3w 数据量还可接受）
- **未来扩展**（百万级数据）：
  ```python
  # 1. Source: 多源候选生成
  candidates_vector = recall_by_vector(query, top_k=1000)
  candidates_tfidf = recall_by_tfidf(query, top_k=500)
  candidates_graph = recall_by_social_graph(user_id, top_k=500)  # 好友听过的
  
  # 2. Hydrator: 批量获取详细信息（避免 N+1 查询）
  candidates = [c.id for c in candidates_vector + candidates_tfidf + ...]
  hydrated = batch_fetch_song_details(candidates)
  
  # 3. Filter: 过滤链
  hydrated = filter_by_language(hydrated)
  hydrated = filter_by_explicit_content(hydrated)
  hydrated = filter_by_previously_played(hydrated, user_id)
  
  # 4. Scorer: 多阶段评分
  hydrated = score_by_semantic_similarity(hydrated, query)
  hydrated = score_by_artist_diversity(hydrated)
  hydrated = apply_weighted_scorer(hydrated)
  
  # 5. Selector: Top-K
  return top_k(hydrated, k=20)
  ```

---

### 5. 特征分层水合 (Hydrator)

**Twitter 的实现**：
```rust
// 不同阶段只加载需要的特征
PreSelectionHydrator:  加载评分用的轻量特征
PostSelectionHydrator: 加载展示用的完整特征（封面、歌词等）
```

**对 VibeCheck 的启发**：
- **当前 SQL**：一次性 `SELECT *`（包含大字段 `lyrics`、`core_lyrics`）
- **优化方案**：
  ```sql
  -- 阶段 1：召回，只查必要字段
  SELECT id, review_vector, lyrics_vector, tfidf_vector
  FROM songs WHERE ...
  
  -- 阶段 2：Top-K 后再水合详细信息
  SELECT id, title, artist, album_cover, review_text, vibe_tags
  FROM songs WHERE id IN (...)
  ```
  减少数据传输量，提升召回速度。

---

## 推荐实施优先级

| 优先级 | 功能 | 复杂度 | 收益 | 估时 |
|--------|------|--------|------|------|
| **P0** | 歌手多样性重排 | 低 | 高 | 2h |
| **P1** | 用户播放历史去重 (exclude_ids) | 低 | 高 | 3h |
| **P1** | 特征分层查询优化 | 中 | 中 | 4h |
| **P2** | 多评分器扩展（流行度、时效性） | 中 | 中 | 6h |
| **P3** | 管道化架构重构 | 高 | 低（当前数据规模） | 2 天 |

---

## 代码示例：歌手多样性重排

```python
# app/services/diversity.py
def apply_artist_diversity(
    results: list[SongSearchResult],
    decay_factor: float = 0.6,
    floor: float = 0.3,
) -> list[SongSearchResult]:
    """
    对搜索结果应用歌手多样性惩罚，防止单一歌手刷屏。
    
    Args:
        decay_factor: 衰减系数 (0~1)，越小惩罚越重
        floor: 最低保留权重，确保不会完全过滤掉好歌
    """
    artist_count: dict[str, int] = {}
    
    for song in results:
        position = artist_count.get(song.artist, 0)
        multiplier = (1 - floor) * (decay_factor ** position) + floor
        song.score *= multiplier
        artist_count[song.artist] = position + 1
    
    # 重新排序
    return sorted(results, key=lambda x: x.score, reverse=True)
```

```python
# app/services/search.py 中调用
async def perform_hybrid_search(...):
    # ... 原有逻辑 ...
    results = [SongSearchResult(...) for row in rows]
    
    # 应用歌手多样性
    results = apply_artist_diversity(results)
    
    return SearchResponse(query=user_query, ...)
```

---

## 总结

Twitter 的推荐架构虽然是为社交网络设计，但其**模块化**、**可扩展性**、**多样性控制**的理念完全适用于音乐推荐。

对 VibeCheck 而言，**短期**可快速实施"歌手多样性"和"用户播放历史去重"，**长期**可考虑引入管道化架构应对数据规模增长。

---

*Generated @ 2026-02-11*
