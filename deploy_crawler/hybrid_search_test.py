import os
import requests
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

def hybrid_search(query_text, top_k=5):
    print(f"\n🔍 正在深度检索: \"{query_text}\"...")
    
    # 获取查询词向量
    query_vec = get_embedding(query_text)
    
    session = Session()
    try:
        # 使用 pgvector 的余弦相似度 <=> 操作符进行检索
        # 由于我们存的是 1024 维，这里直接对比
        # 计算公式：1 - (vector <=> query_vec) 得到相似度 (1是完美匹配)
        search_sql = text("""
            SELECT id, title, artist, vibe_tags, 
                   (1 - (review_vector <=> :q_vec::vector)) as semantic_score,
                   review_text
            FROM songs
            WHERE review_vector IS NOT NULL
            ORDER BY semantic_score DESC
            LIMIT :limit
        """)
        
        results = session.execute(search_sql, {"q_vec": str(query_vec), "limit": top_k}).fetchall()
        
        print(f"\n✨ 为您找到以下最契合的音乐意境：")
        print("-" * 50)
        for i, row in enumerate(results):
            tags = ", ".join(row.vibe_tags) if row.vibe_tags else ""
            print(f"{i+1}. 【{row.title}】 - {row.artist}")
            print(f"   🎭 语义匹配度: {row.semantic_score:.4f}")
            print(f"   🏷️ 标签: {tags}")
            print(f"   📝 AI 评语: {row.review_text[:60]}...")
            print("-" * 50)
            
    finally:
        session.close()

if __name__ == "__main__":
    while True:
        user_query = input("\n请输入你想听的心情、场景或故事 (输入 q 退出): ")
        if user_query.lower() == 'q':
            break
        try:
            hybrid_search(user_query)
        except Exception as e:
            print(f"❌ 检索失败: {e}")
