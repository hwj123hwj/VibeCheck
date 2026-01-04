from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from db_init import Song, get_db_url
from extract_core_lyrics import extract_chorus
import time

engine = create_engine(get_db_url())
Session = sessionmaker(bind=engine)

def batch_update_core_lyrics():
    session = Session()
    try:
        # 1. 一次性获取所有待处理任务的 ID 列表 (这是最稳的写法，避免查询视图动态变动导致的死循环)
        print("🔍 正在扫描数据库待处理项...")
        pending_ids = [r[0] for r in session.execute(
            text("SELECT id FROM songs WHERE lyrics IS NOT NULL AND (core_lyrics IS NULL OR core_lyrics = '')")
        ).fetchall()]
        
        total_pending = len(pending_ids)
        print(f"📦 发现有 {total_pending} 首歌待提取精华歌词...")
        
        if total_pending == 0:
            print("✅ 没有待处理的歌曲。")
            return

        processed = 0
        batch_size = 200
        
        # 2. 遍历 ID 列表进行分批处理
        for i in range(0, total_pending, batch_size):
            batch_ids = pending_ids[i:i + batch_size]
            
            # 获取这一批的具体对象
            songs = session.query(Song).filter(Song.id.in_(batch_ids)).all()
            
            for s in songs:
                try:
                    core = extract_chorus(s.lyrics)
                    # 强补丁：如果是空，存入占位符，防止以后被反复抓取
                    if not core or core.strip() == "":
                        s.core_lyrics = "[N/A]"
                    else:
                        s.core_lyrics = core
                except Exception as e:
                    print(f"  ❌ 提取报错 (ID: {s.id}): {e}")
                    s.core_lyrics = "[ERROR]"
            
            # 每一批提交一次，落袋为安
            session.commit()
            processed += len(songs)
            print(f"🚀 进度: {processed}/{total_pending} ...")
            
    except Exception as e:
        print(f"💥 发生严重错误: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    start_time = time.time()
    batch_update_core_lyrics()
    print(f"✨ 任务已完成！耗时: {time.time() - start_time:.2f} 秒")
