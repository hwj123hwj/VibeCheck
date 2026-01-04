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

# 终极脱水词库 (严禁进入语义分析)
ULTRA_STOP_WORDS = {
    "想听", "给我", "推荐", "一首", "有些", "听听", "有关", "关于", "那些", "的", "了", "在", "我", "你", "他", "她", "，", "。", "！", "？", " ", "”", "“", "歌", "适合", "那种", "一种"
}

def ultra_clean_query(query):
    """只保留最具意境的实词"""
    words = jieba.lcut(query)
    # 彻底排除单字（除了特定的如'雨'、'愁'这种），排除超强停用词
    cleaned = [w for w in words if w not in ULTRA_STOP_WORDS and len(w.strip()) > 1]
    # 如果全被过滤了，保底返回原词
    return cleaned if cleaned else words

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
    print(f"\n🚀 正在进行 5.0 极致语境检索...")
    
    # --- 1. 深度拆解 ---
    cleaned_words = ultra_clean_query(user_query)
    print(f"  🔍 提取核心意境词: {cleaned_words}")
    
    # 策略：识别脱水后的第一个词是否为歌手/歌名关键词
    artist_key = cleaned_words[0] if cleaned_words else ""
    # 纯化意境 Query：把查询词里所有的动作和歌手都删掉，只留剩下的意向
    vibe_words = [w for w in cleaned_words if w != artist_key]
    vibe_query = " ".join(vibe_words) if vibe_words else user_query
    
    # --- 2. 纯净向量化 (只搜意境) ---
    print(f"  🧠 语义对齐目标: \"{vibe_query}\"")
    query_vec = get_embedding(vibe_query)
    
    session = Session()
    try:
        # --- 3. 混合 SQL 5.0 ---
        search_sql = text("""
            WITH scoring_pool AS (
                SELECT 
                    id, title, artist, vibe_tags, review_text,
                    (1 - (review_vector <=> CAST(:q_vec AS vector))) as semantic_score,
                    (
                      CASE WHEN artist ILIKE :artist_q THEN 4.0 ELSE 0 END + -- 加大歌手权重到 4.0
                      CASE WHEN title = :title_exact THEN 2.0 ELSE 0 END + -- 只有完全相等才给标题加分
                      ts_rank_cd(to_tsvector('simple', title || ' ' || segmented_lyrics), 
                               to_tsquery('simple', :ts_q))
                    ) as rational_score
                FROM songs
                WHERE review_vector IS NOT NULL
            )
            SELECT *,
                   (semantic_score * 0.4 + (CASE WHEN rational_score > 4 THEN 4 ELSE rational_score END / 4.0) * 0.6) as final_score
            FROM scoring_pool
            WHERE 
                (artist ILIKE :artist_q AND semantic_score > 0.4) -- 只要提了歌手名，就必须从他的歌里找最像的
                OR (:artist_q = '%%' AND semantic_score > 0.6)   -- 没提歌手名，则全库大搜捕
            ORDER BY final_score DESC
            LIMIT :limit
        """)
        
        ts_query = " | ".join(cleaned_words)

        results = session.execute(search_sql, {
            "q_vec": str(query_vec), 
            "ts_q": ts_query,
            "artist_q": f"%{artist_key}%" if artist_key else "%%",
            "title_exact": artist_key, # 尝试看第一个词是不是标题
            "limit": top_k
        }).fetchall()
        
        print(f"\n🎯 检索结果 (语义纯化 + 歌手强绑定):")
        print("=" * 80)
        for i, row in enumerate(results):
            print(f"{i+1}. 【{row.title}】 - {row.artist}")
            print(f"   📊 深度分析: 语义({row.semantic_score:.3f}) | 匹配({row.rational_score:.3f})")
            print(f"   📝 AI 评语: {row.review_text[:75]}...")
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
