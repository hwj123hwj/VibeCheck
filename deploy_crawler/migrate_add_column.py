from sqlalchemy import create_engine, text
from db_init import get_db_url

def add_is_duplicate_column():
    engine = create_engine(get_db_url())
    try:
        with engine.connect() as conn:
            # 检查列是否存在
            check_sql = "SELECT 1 FROM information_schema.columns WHERE table_name='songs' AND column_name='is_duplicate'"
            result = conn.execute(text(check_sql)).fetchone()
            
            if not result:
                print("正在向 'songs' 表添加 'is_duplicate' 字段...")
                conn.execute(text("ALTER TABLE songs ADD COLUMN is_duplicate BOOLEAN DEFAULT FALSE"))
                conn.commit()
                print("字段添加成功。")
            else:
                print("字段 'is_duplicate' 已存在。")
    except Exception as e:
        print(f"添加字段时出错: {e}")
    finally:
        engine.dispose()

if __name__ == "__main__":
    add_is_duplicate_column()
