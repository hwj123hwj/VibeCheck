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

def get_embedding(text_input):
    """调用 API 获取查询词的向量"""
    headers = {"Authorization": f"Bearer {GUIJI_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": GUIJI_EMB_MODEL, "input": text_input, "encoding_format": "float"}
    resp = requests.post(GUIJI_EMB_URL, headers=headers, json=payload, timeout=10)
    return resp.json()['data'][0]['embedding']

def hybrid_search(user_query, top_k=5):
    print(f"\n� 正在进行 2.0 混合检索: \"{user_query}\"...")
    
    # --- 1. 理性准备: 对查询词进行分词 ---
    # 比如输入 "鲜花种在哪里" -> ["鲜花", "种", "在", "哪里"]
    query_segs = jieba.lcut(user_query)
    ts_query = " | ".join(query_segs) # 变成 "鲜花 | 种 | 在 | 哪里" 用于全文检索
    
    # --- 2. 感性准备: 获取向量 ---
    query_vec = get_embedding(user_query)
    
    session = Session()
    try:
        # --- 3. 混合 SQL 架构 ---
        # semantic_score: 向量相似度 (0-1)
        # rational_score: 关键词匹配度 (使用 ts_rank 计算)
        # final_score: 综合加权排序
        search_sql = text("""
            WITH search_results AS (
                SELECT 
                    id, title, artist, vibe_tags, review_text,
                    (1 - (review_vector <=> CAST(:q_vec AS vector))) as semantic_score,
                    ts_rank_cd(to_tsvector('simple', segmented_lyrics), to_tsquery('simple', :ts_q)) as rational_score
                FROM songs
                WHERE review_vector IS NOT NULL
            )
            SELECT * ,
                   (semantic_score * 0.7 + (CASE WHEN rational_score > 1 THEN 1 ELSE rational_score END) * 0.3) as final_score
            FROM search_results
            ORDER BY final_score DESC
            LIMIT :limit
        """)
        
        results = session.execute(search_sql, {
            "q_vec": str(query_vec), 
            "ts_q": ts_query,
            "limit": top_k
        }).fetchall()
        
        print(f"\n🎯 综合排序结果 (感性 70% + 理性 30%):")
        print("=" * 60)
        for i, row in enumerate(results):
            print(f"{i+1}. 【{row.title}】 - {row.artist}")
            print(f"   📊 综合得分: {row.final_score:.4f} [语义:{row.semantic_score:.3f} | 关键词:{row.rational_score:.3f}]")
            print(f"   📝 AI 评语: {row.review_text[:60]}...")
            print("-" * 60)
            
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
