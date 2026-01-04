from sqlalchemy import create_engine, text
from db_init import get_db_url

def add_column_comments():
    engine = create_engine(get_db_url())
    try:
        with engine.connect() as conn:
            comments = [
                ("is_duplicate", "是否为重复歌曲"),
                ("vibe_tags", "LLM 提取的氛围标签 (JSONB 数组)"),
                ("vibe_scores", "情感维度评分 (JSONB)"),
                ("recommend_scene", "LLM 建议的听歌场景"),
                ("updated_at", "最后更新时间")
            ]
            
            print("正在为 'songs' 表添加字段注释...")
            for col_name, comment in comments:
                sql = f"COMMENT ON COLUMN songs.{col_name} IS '{comment}'"
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    print(f"  √ 已为 '{col_name}' 添加注释")
                except Exception as e:
                    print(f"  ! 为 '{col_name}' 添加注释失败: {e}")
            
            print("所有注释添加完成。")
            
    except Exception as e:
        print(f"连接数据库出错: {e}")
    finally:
        engine.dispose()

if __name__ == "__main__":
    add_column_comments()
