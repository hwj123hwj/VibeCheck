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

# 加载停用词
STOP_WORDS = set()
STOPWORDS_PATH = "stopwords.txt"
if os.path.exists(STOPWORDS_PATH):
    with open(STOPWORDS_PATH, "r", encoding="utf-8") as f:
        STOP_WORDS = {line.strip() for line in f if line.strip()}

def clean_query(query):
    """剔除查询词中的废话"""
    words = jieba.lcut(query)
    cleaned = [w for w in words if w not in STOP_WORDS and len(w.strip()) > 0]
    return cleaned if cleaned else words

def hybrid_search(user_query, top_k=5):
    print(f"\n🚀 正在进行 3.0 深度混合检索: \"{user_query}\"...")
    
    # --- 1. 查询词脱水 ---
    cleaned_words = clean_query(user_query)
    # 提取可能的歌手名（简单逻辑：如果词在 artist 列表里出现过）
    # 这里我们暂且把所有脱水后的词都去匹配 artist 字段
    ts_query = " | ".join(cleaned_words)
    print(f"  🔍 核心检索词: {cleaned_words}")
    
    # --- 2. 获取向量 ---
    query_vec = get_embedding(user_query)
    
    session = Session()
    try:
        # --- 3. 增强版混合 SQL ---
        # artist_boost: 如果歌手名匹配，权重翻倍
        # semantic_score: 语义相似度
        # rational_score: 关键词匹配（针对标题、歌手和歌词）
        search_sql = text("""
            WITH base_scores AS (
                SELECT 
                    id, title, artist, vibe_tags, review_text,
                    (1 - (review_vector <=> CAST(:q_vec AS vector))) as semantic_score,
                    -- 给标题和歌手极高的匹配权重
                    (CASE WHEN artist ILIKE :q_raw THEN 2.0 ELSE 0 END +
                     CASE WHEN title ILIKE :q_raw THEN 1.5 ELSE 0 END +
                     ts_rank_cd(to_tsvector('simple', title || ' ' || artist || ' ' || segmented_lyrics), 
                               to_tsquery('simple', :ts_q))
                    ) as rational_score
                FROM songs
                WHERE review_vector IS NOT NULL
            )
            SELECT *,
                   (semantic_score * 0.6 + (CASE WHEN rational_score > 2 THEN 2 ELSE rational_score END / 2.0) * 0.4) as final_score
            FROM base_scores
            ORDER BY final_score DESC
            LIMIT :limit
        """)
        
        # 为了让歌手匹配更准，我们取脱水词里最像人名的
        potential_artist = f"%{cleaned_words[0]}%" if cleaned_words else f"%{user_query}%"

        results = session.execute(search_sql, {
            "q_vec": str(query_vec), 
            "ts_q": ts_query,
            "q_raw": potential_artist,
            "limit": top_k
        }).fetchall()
        
        print(f"\n🎯 深度排序结果 (感性 60% + 理性 40%):")
        print("=" * 70)
        for i, row in enumerate(results):
            print(f"{i+1}. 【{row.title}】 - {row.artist}")
            print(f"   📊 综合得分: {row.final_score:.4f} [语义:{row.semantic_score:.3f} | 匹配:{row.rational_score:.3f}]")
            print(f"   📝 AI 评语: {row.review_text[:65]}...")
            print("-" * 70)
            
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
