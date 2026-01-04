from sqlalchemy import create_engine, text
from db_init import get_db_url

def migrate():
    engine = create_engine(get_db_url())
    with engine.connect() as conn:
        print("🚀 正在扩容数据库字段...")
        
        # 1. 增加 core_lyrics 文本字段（存 5 句精华）
        try:
            conn.execute(text("ALTER TABLE songs ADD COLUMN IF NOT EXISTS core_lyrics TEXT;"))
            conn.execute(text("COMMENT ON COLUMN songs.core_lyrics IS 'AI或规律算法提取的歌曲精华歌词/副歌';"))
            print("✅ core_lyrics 字段已就绪")
        except Exception as e:
            print(f"⚠️ core_lyrics 报错: {e}")

        # 2. 增加 lyrics_vector 向量字段 (1024 维)
        try:
            conn.execute(text("ALTER TABLE songs ADD COLUMN IF NOT EXISTS lyrics_vector vector(1024);"))
            conn.execute(text("COMMENT ON COLUMN songs.lyrics_vector IS '精华歌词的语义向量索引';"))
            print("✅ lyrics_vector 字段已就绪")
        except Exception as e:
            print(f"⚠️ lyrics_vector 报错: {e}")
            
        conn.commit()
    print("✨ 数据库字段扩容完成！")

if __name__ == "__main__":
    migrate()
