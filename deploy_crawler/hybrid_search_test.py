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

# 2. LLM 配置 (意图路由)
LONGMAO_API_KEY = os.getenv("LONGMAO_API_KEY")
LONGMAO_BASE_URL = os.getenv("LONGMAO_BASE_URL")
LONGMAO_MODEL = os.getenv("LONGMAO_MODEL", "LongCat-Flash-Chat")

def ai_intent_router(query):
    """使用 LLM 识别用户意图，拆解歌手/歌名/意境"""
    prompt = f"""你是一个音乐搜索意图解析引擎。请将用户的输入拆解为 JSON 格式。
输入："{query}"
要求：
1. artist: 提取歌手名，没有则为 null。
2. title: 提取歌名，没有则为 null。
3. vibe: 提取纯粹的心情、场景或故事描述。
4. type: "exact" (如果有明确歌手或歌名) 或 "vibe" (纯搜感觉)。
只输出 JSON。"""
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=LONGMAO_API_KEY, base_url=LONGMAO_BASE_URL)
        response = client.chat.completions.create(
            model=LONGMAO_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        import json
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ AI 路由不可用，切换回基础模式: {e}")
        return {"artist": None, "title": None, "vibe": query, "type": "vibe"}

def hybrid_search(user_query, top_k=5):
    # --- 1. AI 意图路由 ---
    intent = ai_intent_router(user_query)
    print(f"\n🤖 AI 路由结果: {intent}")
    
    # 动态设定权重
    # 如果是 exact 类型，理性权重占 0.8；如果是 vibe 类型，感性向量占 0.8
    v_weight = 0.2 if intent['type'] == 'exact' else 0.7
    r_weight = 1.0 - v_weight
    
    # 纯化向量搜索词
    vibe_query = intent['vibe'] if intent['vibe'] else user_query
    query_vec = get_embedding(vibe_query)
    
    session = Session()
    try:
        # --- 2. 混合 SQL 6.0 ---
        search_sql = text("""
            WITH scoring_pool AS (
                SELECT 
                    id, title, artist, vibe_tags, review_text,
                    (1 - (review_vector <=> CAST(:q_vec AS vector))) as semantic_score,
                    (
                      CASE WHEN artist ILIKE :artist_q THEN 4.0 ELSE 0 END + 
                      CASE WHEN title ILIKE :title_q THEN 3.0 ELSE 0 END + 
                      ts_rank_cd(to_tsvector('simple', title || ' ' || artist || ' ' || segmented_lyrics), 
                               to_tsquery('simple', :ts_q))
                    ) as rational_score
                FROM songs
                WHERE review_vector IS NOT NULL
            )
            SELECT *,
                   (semantic_score * :v_w + (CASE WHEN rational_score > 4 THEN 4 ELSE rational_score END / 4.0) * :r_w) as final_score
            FROM scoring_pool
            WHERE semantic_score > 0.4
            ORDER BY final_score DESC
            LIMIT :limit
        """)
        
        # 将输入分词用于关键词搜索
        cleaned_words = ultra_clean_query(user_query)
        ts_query = " | ".join(cleaned_words)

        results = session.execute(search_sql, {
            "q_vec": str(query_vec), 
            "ts_q": ts_query,
            "artist_q": f"%{intent['artist']}%" if intent['artist'] else "%NONE%",
            "title_q": f"%{intent['title']}%" if intent['title'] else "%NONE%",
            "v_w": v_weight,
            "r_w": r_weight,
            "limit": top_k
        }).fetchall()
        
        print(f"\n🎯 AI 智能驱动检索 (权重: 感性{v_weight*100}% + 理性{r_weight*100}%):")
        print("=" * 80)
        for i, row in enumerate(results):
            print(f"{i+1}. 【{row.title}】 - {row.artist}")
            print(f"   📊 权重分析: 语义({row.semantic_score:.3f}) | 匹配({row.rational_score:.3f})")
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
