from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from db_init import get_db_url
from extract_core_lyrics import extract_chorus

engine = create_engine(get_db_url())
Session = sessionmaker(bind=engine)

def test_famous():
    session = Session()
    try:
        # 指定搜几首你耳熟能详的歌
        target_songs = ["追梦赤子心", "分手快乐", "阴天", "十年", "晴天"]
        
        print(f"🚀 --- 明星曲目精华提取效果测试 ---")
        for title in target_songs:
            # 模糊查询这首歌
            song = session.execute(
                text("SELECT title, artist, lyrics FROM songs WHERE title LIKE :t LIMIT 1"),
                {"t": f"%{title}%"}
            ).fetchone()
            
            if song:
                core = extract_chorus(song.lyrics)
                print(f"\n🎵 【{song.title}】 - {song.artist}")
                print(f"✨ 提取到精华歌词：")
                # 换行显示更清晰
                for i, line in enumerate(core.split('；')):
                    print(f"   {i+1}. {line}")
                print("-" * 50)
            else:
                print(f"❌ 未找到歌曲: {title}")
                
    finally:
        session.close()

if __name__ == "__main__":
    test_famous()
