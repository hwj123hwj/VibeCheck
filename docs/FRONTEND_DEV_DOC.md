# VibeCheck 前端开发文档 (Phase 1: React 设计与实现)

> **项目定位**: 基于氛围与语义的音乐推荐系统 (毕业设计)
> **技术栈**: React 18 + Vite + Tailwind CSS + Lucide React (图标) + Axios
> **当前状态**: 后端 API + 5.3w+ 歌曲数据已就绪

---

## 1. 核心功能与页面结构

### 1.1 页面路由
- `GET /` : 首页 - 品牌展示 + 随机发现 (Vibe 壁放)
- `GET /search` : 搜索页 - 自然语言输入 + 混合检索结果展示
- `GET /song/:id` : 详情页 - 歌曲深度解析 + Vibe 雷达图 + 相似推荐

### 1.2 核心组件
- **SearchInput**: 集成 LLM 意图解析动画的搜索框
- **VibeRadarChart**: 情感五维雷达图 (Energy, Sorrow, Healing, Nostalgic, Loneliness)
- **CompactPlayer**: 基于 `HTML5 Audio` 的极简播放器，支持 30s 试听
- **SongCard**: 瀑布流展示卡片，包含 AI 标签和情感摘要

---

## 2. 播放器 + 歌词同步滚动设计

### 2.1 播放方案 (单一策略)

直接使用 HTML5 `<audio>` 自定义 UI 播放，音源走网易云免费外链：

```
https://music.163.com/song/media/outer/url?id={song_id}.mp3
```

> 免费歌曲可直接播放，VIP 歌曲会返回 30s 试听片段，无需额外降级逻辑。

### 2.2 歌词同步滚动实现

**数据来源**：数据库中的 `lyrics` 字段已被清洗去掉了 LRC 时间戳，因此新增后端接口 **实时获取** 带时间戳的 LRC 歌词：

| 接口 | 说明 | 响应字段 |
| :--- | :--- | :--- |
| `GET /api/songs/{id}/lrc` | 获取 LRC 格式歌词 | `lrc` (原文), `tlyric` (翻译) |

**LRC 格式示例**：
```
[00:00.00]歌名 - 歌手
[00:12.34]我曾经跨过山和大海
[00:18.56]也穿过人山人海
```

**前端实现步骤**：

#### Step 1: 解析 LRC → 结构化数组

```js
// utils/parseLrc.js
export function parseLrc(lrcString) {
  if (!lrcString) return [];
  const lines = lrcString.split('\n');
  const result = [];
  const timeRegex = /\[(\d{2}):(\d{2})\.(\d{2,3})\]/g;

  for (const line of lines) {
    const times = [];
    let match;
    while ((match = timeRegex.exec(line)) !== null) {
      const min = parseInt(match[1]);
      const sec = parseInt(match[2]);
      const ms = parseInt(match[3].padEnd(3, '0'));
      times.push(min * 60 + sec + ms / 1000);
    }
    const text = line.replace(timeRegex, '').trim();
    if (text) {
      times.forEach(time => result.push({ time, text }));
    }
  }
  return result.sort((a, b) => a.time - b.time);
}
```

#### Step 2: 用 `timeupdate` 事件驱动高亮行切换

```jsx
// components/LyricsScroller.jsx
import { useState, useRef, useEffect, useCallback } from 'react';

export default function LyricsScroller({ lyrics, audioRef }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const containerRef = useRef(null);

  // 监听 audio 时间变化，二分查找当前行
  const handleTimeUpdate = useCallback(() => {
    const currentTime = audioRef.current?.currentTime ?? 0;
    let idx = 0;
    for (let i = lyrics.length - 1; i >= 0; i--) {
      if (currentTime >= lyrics[i].time) { idx = i; break; }
    }
    setActiveIndex(idx);
  }, [lyrics, audioRef]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.addEventListener('timeupdate', handleTimeUpdate);
    return () => audio.removeEventListener('timeupdate', handleTimeUpdate);
  }, [audioRef, handleTimeUpdate]);

  // 自动滚动到高亮行
  useEffect(() => {
    const activeEl = containerRef.current?.children[activeIndex];
    activeEl?.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, [activeIndex]);

  return (
    <div ref={containerRef} className="h-64 overflow-y-auto lyrics-container">
      {lyrics.map((line, i) => (
        <p
          key={i}
          className={`py-2 text-center transition-all duration-300 ${
            i === activeIndex
              ? 'text-white text-lg font-bold scale-105'
              : 'text-gray-500 text-sm'
          }`}
        >
          {line.text}
        </p>
      ))}
    </div>
  );
}
```

#### Step 3: 在歌曲详情页组装

```jsx
// pages/SongDetail.jsx (关键片段)
const audioRef = useRef(null);
const [lrcLines, setLrcLines] = useState([]);

useEffect(() => {
  axios.get(`/api/songs/${id}/lrc`).then(res => {
    setLrcLines(parseLrc(res.data.lrc));
  });
}, [id]);

return (
  <>
    <audio
      ref={audioRef}
      src={`https://music.163.com/song/media/outer/url?id=${id}.mp3`}
      controls
    />
    <LyricsScroller lyrics={lrcLines} audioRef={audioRef} />
  </>
);
```

#### 视觉效果 CSS

```css
.lyrics-container {
  mask-image: linear-gradient(transparent, black 20%, black 80%, transparent);
  -webkit-mask-image: linear-gradient(transparent, black 20%, black 80%, transparent);
  scroll-behavior: smooth;
}
```

> 上下边缘的渐隐遮罩 (mask-image) 营造"聚焦当前行"的沉浸感。

**开发任务**:
1. [ ] 封装 `parseLrc` 工具函数 + 单元测试
2. [ ] 实现 `LyricsScroller` 组件
3. [ ] 自定义播放器 UI (进度条、音量、封面旋转)

---

## 3. 后端 API 对接规范

### 3.1 基础配置
- **Base URL**: `http://localhost:8000/api`
- **CORS**: 已在后端开启，允许 `localhost:5173` 访问

### 3.2 重点接口映射
| 功能 | 接口地址 | 响应字段 |
| :--- | :--- | :--- |
| 搜索 | `/search?q={query}&top_k=10` | `results`, `intent_type` |
| 详情 | `/songs/{id}` | `vibe_scores`, `review_text`, `core_lyrics` |
| LRC 歌词 | `/songs/{id}/lrc` | `lrc`, `tlyric` |
| 相似 | `/recommend/{id}` | `recommendations` |
| 随机 | `/songs/random/list` | 首页 Initial Data |

---

## 4. UI 视觉风格 (Design Language)

- **色调**: 幽邃灰 (#0A0A0A) + 网易红 (#E91E63) + 霓虹蓝 (氛围色)
- **字体**: 系统默认无衬线 + 核心歌词用衬线体 (Serif)
- **交互**: 
    - 搜索时进度条提示 "LLM 正在解析意图..."
    - 卡片 Hover 触发雷达图渐入效果

---

## 5. 开发阶段验证清单

在正式开发前，需在浏览器 Console 完成以下验证：
- [ ] 随机抽样 10 个 ID 访问 `media/outer/url` 测试连通性
- [ ] 验证 `vibe_scores` 是否能正确渲染雷达图
- [ ] 调用 `/api/songs/{id}/lrc` 确认 LRC 时间戳完整返回
- [ ] 验证 `parseLrc` 解析结果与 `timeupdate` 同步效果

---

## 6. 后续扩展计划

- **跨平台**: 为 Flutter 桌面端预留 `Bridge` 接口
- **个性化**: 集成 `song_events` 记录用户点击行为，实现本地反馈循环
- **动态评语**: 允许用户对当前推荐结果提出"再感伤一点"等修正要求

