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
BATCH_SIZE = 15        # 每次 API 调用处理 15 首歌
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

def process_lyrics_vectorization():
    session = Session()
    try:
        # 1. 查找【精华歌词已提取】但【向量未生成】的歌曲
        query = session.query(Song).filter(
            and_(
                Song.core_lyrics != None,
                Song.core_lyrics != '',
                Song.lyrics_vector == None,
                Song.is_duplicate == False
            )
        )
        
        total_pending = query.count()
        print(f"📦 发现 {total_pending} 份精华歌词待生成语义向量索引...")

        processed_count = 0
        while True:
            # 2. 分页获取一批
            songs_batch = query.limit(BATCH_SIZE).all()
            if not songs_batch:
                break

            # 3. 准备待向量化的文本
            texts_to_embed = []
            for s in songs_batch:
                # 只对已经脱水后的金句进项向量化
                texts_to_embed.append(s.core_lyrics[:1500])

            # 4. 获取向量
            embeddings = get_embeddings_batch(texts_to_embed)
            
            if embeddings and len(embeddings) == len(songs_batch):
                # 5. 更新回数据库
                for i, song in enumerate(songs_batch):
                    song.lyrics_vector = embeddings[i]
                
                session.commit()
                processed_count += len(songs_batch)
                print(f"✅ 已完成: {processed_count}/{total_pending}")
                
                # 6. 频率控制
                time.sleep(SLEEP_BETWEEN_BATCH)
            else:
                print("⛔ Batch 获取失败，跳过并进入下一个循环...")
                time.sleep(5)

        print(f"🎉 全部核心歌词向量化完毕，共处理 {processed_count} 首。")

    finally:
        session.close()

if __name__ == "__main__":
    if not API_KEY:
        print("❌ 错误: 请先在 .env 中设置 GUIJI_API_KEY")
    else:
        process_lyrics_vectorization()
