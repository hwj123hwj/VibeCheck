import os
import requests
import jieba
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from db_init import get_db_url

# 1. 环境配置
load_dotenv()
GUIJI_API_KEY = os.getenv("GUIJI_API_KEY")
GUIJI_EMB_URL = os.getenv("GUIJI_EMB_URL", "https://api.siliconflow.cn/v1/embeddings")
GUIJI_EMB_MODEL = os.getenv("GUIJI_EMB_MODEL", "BAAI/bge-m3")

engine = create_engine(get_db_url())
Session = sessionmaker(bind=engine)

# 扩展停用词库
STOPWORDS_PATH = "stopwords.txt"
EXTENDED_STOP_WORDS = {"一首歌", "的一首", "一种", "的一", "对于", "关于", "我想", "听听", "的", "了", "在", "，", "。", "！", "？", " ", "”", "“", "歌"}
if os.path.exists(STOPWORDS_PATH):
    with open(STOPWORDS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            EXTENDED_STOP_WORDS.add(line.strip())

def get_embedding(text_input):
    """调用 API 获取查询词的向量"""
    headers = {"Authorization": f"Bearer {GUIJI_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": GUIJI_EMB_MODEL, "input": text_input, "encoding_format": "float"}
    resp = requests.post(GUIJI_EMB_URL, headers=headers, json=payload, timeout=10)
    return resp.json()['data'][0]['embedding']

def deep_clean_query(query):
    """极其激进的查询词净化"""
    words = jieba.lcut(query)
    # 过滤掉停用词，且只要长度大于1的实词，除非是特定的歌手名/歌名
    cleaned = [w for w in words if w not in EXTENDED_STOP_WORDS and len(w.strip()) > 0]
    return cleaned if cleaned else words

def hybrid_search(user_query, top_k=5):
    print(f"\n🚀 正在进行 4.0 意图识别混合检索...")
    
    # --- 1. 拆解意图 ---
    cleaned_words = deep_clean_query(user_query)
    print(f"  🔍 识别核心意图: {cleaned_words}")
    
    # 尝试提取歌手名 (这里简单地认为第一个词可能是歌手)
    potential_artist = cleaned_words[0] if cleaned_words else ""
    # 提取纯意境词 (去掉歌手名) 
    vibe_query = "".join(cleaned_words[1:]) if len(cleaned_words) > 1 else user_query
    
    # --- 2. 获取向量 (只拿意境部分去搜语义，防止歌手名干扰) ---
    print(f"  🧠 语义对齐目标: \"{vibe_query}\"")
    query_vec = get_embedding(vibe_query)
    
    session = Session()
    try:
        # --- 3. 混合 SQL 4.0 ---
        # 引入【标题关键词命中】的爆炸加分策略
        search_sql = text("""
            WITH scoring_pool AS (
                SELECT 
                    id, title, artist, vibe_tags, review_text,
                    (1 - (review_vector <=> CAST(:q_vec AS vector))) as semantic_score,
                    -- 理性匹配逻辑
                    (
                      CASE WHEN artist ILIKE :artist_q THEN 3.0 ELSE 0 END + -- 歌手匹配给最高优先级
                      CASE WHEN title ILIKE :vibe_first THEN 1.5 ELSE 0 END + -- 标题命中关键动作给高分
                      ts_rank_cd(to_tsvector('simple', title || ' ' || segmented_lyrics), 
                               to_tsquery('simple', :ts_q))
                    ) as rational_score
                FROM songs
                WHERE review_vector IS NOT NULL
            )
            SELECT *,
                   (semantic_score * 0.5 + (CASE WHEN rational_score > 3 THEN 3 ELSE rational_score END / 3.0) * 0.5) as final_score
            FROM scoring_pool
            WHERE artist ILIKE :artist_q OR semantic_score > 0.5 -- 缩小范围，梁静茹优先
            ORDER BY final_score DESC
            LIMIT :limit
        """)
        
        # 将脱水后的词连成 tsquery
        ts_query = " | ".join(cleaned_words)
        vibe_first = f"%{cleaned_words[1]}%" if len(cleaned_words) > 1 else "%NONE%"

        results = session.execute(search_sql, {
            "q_vec": str(query_vec), 
            "ts_q": ts_query,
            "artist_q": f"%{potential_artist}%",
            "vibe_first": vibe_first,
            "limit": top_k
        }).fetchall()
        
        print(f"\n🎯 智能检索结果 (歌手权重补正 + 语义对齐):")
        print("=" * 80)
        for i, row in enumerate(results):
            print(f"{i+1}. 【{row.title}】 - {row.artist}")
            print(f"   📊 权重分析: 语义({row.semantic_score:.3f}) + 命中({row.rational_score:.3f}) -> 综分:{row.final_score:.4f}")
            print(f"   📝 AI 评语: {row.review_text[:70]}...")
            print("-" * 80)
            
    finally:
        session.close()

if __name__ == "__main__":
    # 第一次运行加载一下 jieba 字典
    # print("正在预热分词器...")
    # jieba.lcut("你好")
    
    while True:
        user_query = input("\n请输入你想听的心情、场景或歌词碎片 (输入 q 退出): ")
        if user_query.lower() == 'q':
            break
        if not user_query.strip():
            continue
        try:
            hybrid_search(user_query)
        except Exception as e:
            print(f"❌ 检索失败: {e}")
            # 如果是 tsquery 报错，通常是因为特殊字符，这里简单处理下
            if "syntax error" in str(e).lower():
                print("💡 提示：请尝试输入更简单的关键词。")
