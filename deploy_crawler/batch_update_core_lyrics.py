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
        # 1. 查找待处理歌曲
        pending_songs_query = session.query(Song).filter(
            Song.lyrics != None,
            (Song.core_lyrics == None) | (Song.core_lyrics == '')
        )
        
        total_pending = pending_songs_query.count()
        print(f"📦 发现有 {total_pending} 首歌待提取精华歌词...")
        
        if total_pending == 0:
            print("✅ 没有待处理的歌曲。")
            return

        batch_size = 200
        processed = 0
        
        # 为了防止死循环，我们记录一下连续出现相同结果的次数
        last_id = None
        repeat_count = 0

        while True:
            # 2. 获取一批
            songs = pending_songs_query.limit(batch_size).all()
            if not songs:
                break
            
            # 安全检查：如果连续两次抓到的第一个 ID 一样，说明更新没生效
            if last_id == songs[0].id:
                print(f"⚠️ 检测到数据更新瓶颈 (ID: {songs[0].id})，正在尝试强制修复...")
                repeat_count += 1
                if repeat_count > 3:
                    print("❌ 无法跳出的死循环，程序终止。请检查数据库状态。")
                    break
            else:
                last_id = songs[0].id
                repeat_count = 0

            # 3. 逐一提取并更新
            for s in songs:
                try:
                    core = extract_chorus(s.lyrics)
                    # 核心加固：如果提取结果还是空，强制存入 [N/A]
                    if not core or core.strip() == "":
                        s.core_lyrics = "[N/A]"
                    else:
                        s.core_lyrics = core
                except Exception as e:
                    print(f"  ❌ 歌曲 {s.title} (ID: {s.id}) 提取错误: {e}")
                    s.core_lyrics = "[ERROR]"
            
            session.commit()
            processed += len(songs)
            print(f"🚀 已处理 {processed} 首...")
            
    except Exception as e:
        print(f"💥 发生严重错误: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    start_time = time.time()
    batch_update_core_lyrics()
    print(f"✨ 任务结束！耗时: {time.time() - start_time:.2f} 秒")
