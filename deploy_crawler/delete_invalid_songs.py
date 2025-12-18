from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from db_init import Song, get_db_url

# 1. 初始化数据库连接
engine = create_engine(get_db_url())
Session = sessionmaker(bind=engine)
session = Session()

def delete_short_lyrics(min_length=10):
    print(f"正在准备删除歌词长度小于 {min_length} 个字符的异常歌曲...")
    
    # 首先查询一下符合条件的数量，给用户一个预期
    # 注意：func.length 在 PostgreSQL 中统计的是字符数
    try:
        query = session.query(Song).filter(
            (Song.lyrics == None) | (func.length(Song.lyrics) < min_length)
        )
        total_to_delete = query.count()
        
        if total_to_delete == 0:
            print("没有发现歌词过短或为空的歌曲，无需删除。")
            return

        print(f"发现 {total_to_delete} 首歌曲歌词过短或为空，准备删除...")
        
        # 执行强制删除
        query.delete(synchronize_session=False)
        session.commit()
        
        print(f"成功删除 {total_to_delete} 条无效记录。")
        
    except Exception as e:
        session.rollback()
        print(f"执行删除时出错: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    delete_short_lyrics(10)
