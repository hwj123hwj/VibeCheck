import os
import time
import json
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, and_, or_, text
from sqlalchemy.orm import sessionmaker
from db_init import Song, get_db_url

# 1. 基础配置
load_dotenv()
API_KEY = os.getenv("GUIJI_API_KEY")
API_URL = os.getenv("GUIJI_EMB_URL", "https://api.siliconflow.cn/v1/embeddings")
MODEL = os.getenv("GUIJI_EMB_MODEL", "BAAI/bge-m3")

# 频率控制配置 (适配 L0 级别)
BATCH_SIZE = 15        # 每次 API 调用处理 15 首歌 (SiliconFlow 通常支持 1-50)
SLEEP_BETWEEN_BATCH = 1.0  # 每个 Batch 后的等待时间 (秒)
MAX_RETRIES = 5        # 429 报错后的重试次数

# 2. 数据库连接
engine = create_engine(get_db_url())
Session = sessionmaker(bind=engine)

def get_embeddings_batch(texts):
    """
    调用硅基流动批量获取 Embedding
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "input": texts,
        "encoding_format": "float"
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=20)
            if response.status_code == 200:
                result = response.json()
                # 返回的是有序列表，对应 input 顺序
                return [item['embedding'] for item in result['data']]
            elif response.status_code == 429:
                wait_time = 2 ** attempt + 5
                print(f"  ⚠️ 触发频率限制 (429)，正在冷却 {wait_time} 秒...")
                time.sleep(wait_time)
            else:
                print(f"  ❌ API 返回错误 {response.status_code}: {response.text}")
                return None
        except Exception as e:
            print(f"  💥 网络异常 ({attempt+1}/{MAX_RETRIES}): {e}")
            time.sleep(2)
    return None

def process_batch_vectorization():
    session = Session()
    try:
        # 1. 查找还未生成向量的歌曲
        # 排除重复歌曲，优先处理有评语的
        query = session.query(Song).filter(
            and_(
                Song.review_text != None,
                Song.review_vector == None,
                Song.is_duplicate == False
            )
        )
        
        total_pending = query.count()
        print(f"📦 发现 {total_pending} 首歌曲待生成语义向量...")

        processed_count = 0
        while True:
            # 2. 分页获取一批
            songs_batch = query.limit(BATCH_SIZE).all()
            if not songs_batch:
                break

            # 3. 准备拼接后的文本
            texts_to_embed = []
            for s in songs_batch:
                # 拼接策略: Tags + Review + Scene
                tags_str = " ".join(s.vibe_tags) if s.vibe_tags else ""
                combined_text = (
                    f"Tags: {tags_str}。 "
                    f"Review: {s.review_text}。 "
                    f"Scene: {s.recommend_scene or ''}"
                )
                # 截断超长文本 (BAAI/bge-m3 支持 8192 token，一般不会超，但保护一下)
                texts_to_embed.append(combined_text[:1500])

            # 4. 获取向量
            embeddings = get_embeddings_batch(texts_to_embed)
            
            if embeddings and len(embeddings) == len(songs_batch):
                # 5. 更新回数据库
                # 注意：SQLAlchemy 更新 Vector 字段通常需要 list[float]
                for i, song in enumerate(songs_batch):
                    song.review_vector = embeddings[i]
                
                session.commit()
                processed_count += len(songs_batch)
                print(f"✅ 已完成: {processed_count}/{total_pending}")
                
                # 6. 频率控制
                time.sleep(SLEEP_BETWEEN_BATCH)
            else:
                print("⛔ Batch 获取失败，跳过并进入下一个循环...")
                time.sleep(5)

        print(f"🎉 全部任务执行完毕，共处理 {processed_count} 首。")

    finally:
        session.close()

if __name__ == "__main__":
    if not API_KEY:
        print("❌ 错误: 请先在 .env 中设置 GUIJI_API_KEY")
    else:
        process_batch_vectorization()
