# 毕设改进计划

> 整理时间：2026-03-20
> 
> 基于导师反馈的改进方向

---

## 一、导师反馈问题汇总

### 1. 题目"多维语义理解"不准确

**问题**：题目说"多维语义理解"，但实际只做了向量空间，没有真正的多维度。

**真正的多维应该包括**：
- 音频特征
- 情感分析
- 文本语义
- 等多个维度

**解决方案**：
- [ ] 修改题目，去掉"多维"
- [ ] 或补充其他维度的特征

**新题目建议**：
> 基于语义理解与用户偏好学习的华语流行歌曲推荐系统设计与实现

---

### 2. 公式缺乏论证

**问题**：论文中的公式太随意，参数设置没有解释：
- 为什么这样设置参数？
- 为什么这样设置效果更好？
- 缺乏实验对比和理论支撑

**解决方案**：
- [ ] 补充消融实验
- [ ] 参数敏感性分析
- [ ] 对比实验（TF-IDF vs LLM Embedding）
- [ ] 用户调研验证

**参考论证方法**：
1. **对比实验**：你的系统 vs 网易云推荐 vs 随机推荐，用户盲测打分
2. **案例分析**：用具体案例说明"为什么这样推荐"
3. **诚实讨论局限性**：论文里直接写氛围推荐效果评估的主观性

---

### 3. 系统复杂度太低

**当前技术栈**：
- 前端: React
- 后端: FastAPI
- 数据库: PostgreSQL
- 部署: 腾讯云

**问题**：技术栈简单，工作量显得不足。

**可能的改进方向**：
- [ ] 用户画像 + 偏好学习模块
- [ ] 多样性控制（去重、打散）
- [ ] Redis 缓存层
- [ ] 定时任务更新特征
- [ ] 音频特征提取（librosa）

---

### 4. 缺少推荐系统理论支撑

**问题**：没有理论支撑 = 像玩具项目，只是"歌词语义搜索"，不能算"推荐系统"。

**解决方案**：
- [ ] 明确定位：**基于内容的音乐推荐系统**
- [ ] 引用经典论文：Content-Based Recommendation 理论框架
- [ ] 强调创新点：用 LLM embedding 替代传统 TF-IDF

**可引用的经典论文**：
1. Pazzani & Billsus (2007) - "Content-Based Recommendation Systems"
2. Balabanović & Shoham (1997) - "Content-Based, Collaborative Recommendation"
3. Van den Oord et al. (2013) - "Deep content-based music recommendation"

---

## 二、改进优先级

| 优先级 | 任务 | 状态 | 预计时间 |
|--------|------|------|----------|
| 🔴 高 | 修改题目（去掉"多维"） | 待做 | 1天 |
| 🔴 高 | 强化内容推荐理论框架 | 待做 | 2天 |
| 🔴 高 | 用户画像 + 偏好学习模块 | 待做 | 3-5天 |
| 🟡 中 | 多样性控制 | 待做 | 1天 |
| 🟡 中 | 公式论证 + 对比实验 | 待做 | 2天 |
| 🟡 中 | Redis 缓存层 | 待做 | 1天 |
| 🟢 低 | 音频特征提取 | 暂缓 | 后续扩展 |

---

## 三、扩展路线图

```
v1.0 当前              v1.1 近期              v2.0 中期              v3.0 远期
    │                      │                      │                      │
语义召回              用户画像               音频特征              协同过滤
基础排序              多样性控制             多维融合              实时推荐
前后端联调            Redis缓存              A/B测试               深度排序模型
```

---

## 四、参考文献

1. xAI. x-algorithm: Algorithm powering the For You feed on X. GitHub, 2024. https://github.com/xai-org/x-algorithm

2. Pazzani M J, Billsus D. Content-based recommendation systems[M]//The adaptive web. Springer, 2007: 325-341.

3. Balabanović M, Shoham Y. Content-based, collaborative recommendation[J]. Communications of the ACM, 1997, 40(3): 66-72.

4. Van den Oord A, Dieleman S, Schrauwen B. Deep content-based music recommendation[C]//Advances in neural information processing systems. 2013: 2643-2651.