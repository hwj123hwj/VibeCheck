# VibeCheck → Go 重构指南

本文档专门为将 Python/FastAPI 后端重构为 Go 而写，包含完整的对应关系、推荐方案和已知坑点。

---

## 一、整体对应关系

| Python 层 | Go 对应 | 说明 |
|---|---|---|
| FastAPI | Gin 或 Echo | 路由、中间件、参数绑定均有直接对应 |
| SQLAlchemy async | pgx v5 直接写 SQL | 原代码 SQL 都是手写的，迁移容易 |
| pydantic-settings | viper + godotenv | 读取 .env 配置 |
| TTLCache | go-cache 或 ristretto | 内存 KV 缓存，TTL 支持 |
| httpx AsyncClient | net/http 标准库 | Go 原生 HTTP client 性能更好 |
| asyncio.gather | errgroup | 并发多个请求，有错误传播 |
| StreamingResponse | io.Copy + http.ResponseWriter | Go 做流式代理更自然 |
| Pydantic model | struct + json tag | 直接对应 |

---

## 二、推荐的 Go 项目结构

```
vibecheck-go/
├── cmd/
│   └── server/main.go        # 入口，初始化依赖，启动 HTTP 服务
├── internal/
│   ├── config/config.go      # 读取 .env，定义 Config struct
│   ├── db/db.go              # pgx 连接池初始化
│   ├── model/song.go         # Song struct（对应数据库字段）
│   ├── schema/               # 请求/响应 struct（对应 schemas.py）
│   │   ├── search.go
│   │   └── recommend.go
│   ├── service/
│   │   ├── embedding.go      # 调用硅基流动
│   │   ├── llm.go            # 调用 LongMao
│   │   ├── search.go         # 混合搜索核心
│   │   └── recommend.go      # 推荐核心 + 缓存
│   └── handler/              # 对应 routers/
│       ├── songs.go
│       ├── search.go
│       └── recommend.go
├── go.mod
└── go.sum
```

---

## 三、pgvector 适配

这是整个重构里最需要注意的部分。

**依赖**：`github.com/pgvector/pgvector-go`

```go
import "github.com/pgvector/pgvector-go"

// 读取向量
var reviewVector pgvector.Vector
row.Scan(&reviewVector)

// 写入向量（向量化结果是 []float32）
vec := pgvector.NewVector(embedding) // embedding 是 []float32
```

**向量检索 SQL 写法**（和 Python 版完全一致，pgx 支持直接传参）：

```go
sql := `
    SELECT id, title, artist,
           1 - (review_vector <=> $1) AS review_sim
    FROM songs
    WHERE review_vector IS NOT NULL
    ORDER BY review_vector <=> $1
    LIMIT $2
`
rows, err := pool.Query(ctx, sql, pgvector.NewVector(queryVec), topK)
```

**坑点**：pgvector-go 要求 pgx v5，不兼容 v4。确认依赖版本：
```
github.com/jackc/pgx/v5
github.com/pgvector/pgvector-go
```

---

## 四、并发请求（对应 asyncio.gather）

搜索时 LLM 意图解析和 Embedding 向量化是并发的：

```python
# Python
intent, query_vec = await asyncio.gather(
    parse_search_intent(user_query),
    get_embedding(user_query),
)
```

Go 用 `errgroup`：

```go
import "golang.org/x/sync/errgroup"

g, ctx := errgroup.WithContext(ctx)

var intent IntentResult
var queryVec []float32

g.Go(func() error {
    var err error
    intent, err = ParseSearchIntent(ctx, query)
    return err
})

g.Go(func() error {
    var err error
    queryVec, err = GetEmbedding(ctx, query)
    return err
})

if err := g.Wait(); err != nil {
    return err
}
```

---

## 五、流式音频代理

Python 的 `StreamingResponse` 在 Go 里直接用标准库，反而更简单：

```go
func ProxyAudio(w http.ResponseWriter, r *http.Request, audioURL string) {
    req, _ := http.NewRequest("GET", audioURL, nil)
    req.Header.Set("Referer", "https://music.163.com/")
    req.Header.Set("User-Agent", "Mozilla/5.0 ...")

    resp, err := http.DefaultClient.Do(req)
    if err != nil || resp.StatusCode != 200 {
        http.Error(w, "audio unavailable", 404)
        return
    }
    defer resp.Body.Close()

    w.Header().Set("Content-Type", resp.Header.Get("Content-Type"))
    if cl := resp.Header.Get("Content-Length"); cl != "" {
        w.Header().Set("Content-Length", cl)
    }
    io.Copy(w, resp.Body)  // 流式转发，不会把整个文件读入内存
}
```

---

## 六、内存缓存（对应 TTLCache）

```go
import "github.com/patrickmn/go-cache"

// 初始化：10小时过期，每30分钟清理一次过期项
c := cache.New(10*time.Hour, 30*time.Minute)

// 写入
c.Set(cacheKey, results, cache.DefaultExpiration)

// 读取
if cached, found := c.Get(cacheKey); found {
    return cached.([]SongResult), nil
}
```

**cache key** 的生成：Python 里是 tuple，Go 里用字符串拼接：

```go
import "fmt"
key := fmt.Sprintf("%s:%d:%.2f:%.2f:%.2f", songID, topK, wReview, wLyrics, wTfidf)
```

---

## 七、jieba 分词

Python 用 `jieba`，Go 对应库是 `github.com/yanyiwu/gojieba`。

```go
import "github.com/yanyiwu/gojieba"

jb := gojieba.NewJieba()
defer jb.Free()

words := jb.CutForSearch("深夜一个人emo", true)
```

**坑点**：

1. gojieba 依赖 cgo，交叉编译（比如 Mac 编译 Linux 二进制）时需要配置 CGO 环境，或改用纯 Go 实现的分词库（如 `github.com/go-ego/gse`）。
2. gojieba 和 Python jieba 的分词结果**有细微差异**，会影响 TF-IDF 关键词搜索的召回率，但影响有限（TF-IDF 权重本来就只占 0.1~0.2）。
3. 如果不想处理 cgo，搜歌名/歌手模式完全不需要分词，只有 auto 模式的关键词匹配部分依赖分词。

---

## 八、LLM 和 Embedding 接口

两个外部 API 都兼容 OpenAI SDK 格式，Go 用官方库：

```go
import "github.com/openai/openai-go"

// LLM（LongMao）
client := openai.NewClient(
    option.WithAPIKey(cfg.LongmaoAPIKey),
    option.WithBaseURL(cfg.LongmaoBaseURL),
)

resp, err := client.Chat.Completions.New(ctx, openai.ChatCompletionNewParams{
    Model:    openai.F(cfg.LongmaoModel),
    Messages: openai.F(messages),
})

// Embedding（硅基流动）
embClient := openai.NewClient(
    option.WithAPIKey(cfg.GuijiAPIKey),
    option.WithBaseURL("https://api.siliconflow.cn/v1"),
)

embResp, err := embClient.Embeddings.New(ctx, openai.EmbeddingNewParams{
    Model: openai.F("BAAI/bge-m3"),
    Input: openai.F[openai.EmbeddingNewParamsInputUnion](
        openai.EmbeddingNewParamsInputArrayOfStrings([]string{text}),
    ),
})
// 返回的是 []float64，转 []float32 给 pgvector
```

**注意**：返回的 embedding 是 `[]float64`，pgvector-go 需要 `[]float32`，需要手动转换。

---

## 九、SQL 中的 JSONB 操作

Python 代码里有几处 JSONB 查询，Go 里直接传参即可，无需特殊处理：

```go
// tfidf_vector 关键词重叠计算（保持和 Python 版相同的 SQL）
sql := `
    SELECT COUNT(*)::float
    FROM jsonb_object_keys(COALESCE(tfidf_vector, '{}'::jsonb)) AS k(key)
    WHERE k.key = ANY($1)
`
// $1 传 []string
rows, _ := pool.Query(ctx, sql, tfidfKeys)
```

---

## 十、推荐去重逻辑

Python 版用正则提取主标题，Go 版直接翻译：

```go
import "regexp"

var (
    bracketRe = regexp.MustCompile(`[\x28\uff08\x5b\u3010][^\x29\uff09\x5d\u3011]*[\x29\uff09\x5d\u3011]`)
    versionRe = regexp.MustCompile(`(?i)(cover|live|remix|dj|翻唱|版|ver\.?).*$`)
    spaceRe   = regexp.MustCompile(`\s+.*$`)
)

func baseTitle(title string) string {
    t := bracketRe.ReplaceAllString(title, "")
    t = versionRe.ReplaceAllString(t, "")
    t = spaceRe.ReplaceAllString(t, "")
    return strings.TrimSpace(t)
}
```

---

## 十一、建议重构顺序

按依赖复杂度从低到高：

1. **`handler/songs.go`** — 歌曲详情、随机列表、情绪分区，只涉及 PostgreSQL 查询，无外部 API 调用，最简单
2. **`service/embedding.go`** — 单个外部 API 调用，有了这个后面都能用
3. **`handler/search.go`** — 搜索逻辑，依赖 embedding + llm + pgvector，可以先只实现 title/artist 模式，再加 vibe/lyrics
4. **`handler/recommend.go`** — 最复杂，依赖向量检索 + 缓存 + 去重，放最后

每个 handler 实现完可以直接对比接口响应，前端完全不用改。

---

## 十二、前端无需改动

Go 服务保持和 Python 完全相同的接口路径和响应格式，前端代码零改动。

唯一需要注意的是响应的 JSON 字段名大小写：Python/Pydantic 默认是 `snake_case`，Go struct 的 json tag 也要写成 `snake_case`：

```go
type SongSearchResult struct {
    ID          string   `json:"id"`
    Title       string   `json:"title"`
    Artist      string   `json:"artist"`
    AlbumCover  *string  `json:"album_cover"`
    ReviewText  *string  `json:"review_text"`
    Score       float64  `json:"score"`
    ReviewScore *float64 `json:"review_score"`
    LyricsScore *float64 `json:"lyrics_score"`
}
```
