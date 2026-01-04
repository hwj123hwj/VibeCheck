from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from db_init import get_db_url
from extract_core_lyrics import extract_chorus
import time

engine = create_engine(get_db_url())
Session = sessionmaker(bind=engine)

def batch_update_core_lyrics():
    session = Session()
    try:
        # 1. 找出所有 core_lyrics 还是空的歌
        count_sql = text("SELECT count(*) FROM songs WHERE lyrics IS NOT NULL AND (core_lyrics IS NULL OR core_lyrics = '')")
        total_pending = session.execute(count_sql).scalar()
        print(f"📦 发现有 {total_pending} 首歌待提取精华歌词...")
        
        batch_size = 500
        processed = 0
        
        while True:
            # 2. 分批抓取
            songs = session.execute(
                text("SELECT id, lyrics FROM songs WHERE lyrics IS NOT NULL AND (core_lyrics IS NULL OR core_lyrics = '') LIMIT :size"),
                {"size": batch_size}
            ).fetchall()
            
            if not songs:
                break
                
            # 3. 批量处理并更新
            for s in songs:
                core = extract_chorus(s.lyrics)
                session.execute(
                    text("UPDATE songs SET core_lyrics = :core WHERE id = :id"),
                    {"core": core, "id": s.id}
                )
            
            session.commit()
            processed += len(songs)
            print(f"🚀 已处理 {processed}/{total_pending} ...")
            
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    start_time = time.time()
    batch_update_core_lyrics()
    print(f"✨ 处理完成！耗时: {time.time() - start_time:.2f} 秒")
