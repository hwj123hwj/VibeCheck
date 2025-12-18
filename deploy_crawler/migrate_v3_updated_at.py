from sqlalchemy import create_engine, text
from db_init import get_db_url

def migrate_v3_updated_at():
    engine = create_engine(get_db_url())
    try:
        with engine.connect() as conn:
            # 检查列是否存在
            check_sql = "SELECT 1 FROM information_schema.columns WHERE table_name='songs' AND column_name='updated_at'"
            result = conn.execute(text(check_sql)).fetchone()
            
            if not result:
                print("正在向 'songs' 表添加 'updated_at' 字段...")
                # PostgreSQL 的 ALTER TABLE 增加带默认值的 TIMESTAMP 字段
                conn.execute(text("ALTER TABLE songs ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                conn.commit()
                print("字段 'updated_at' 添加成功。")
            else:
                print("字段 'updated_at' 已存在。")
    except Exception as e:
        print(f"迁移时出错: {e}")
    finally:
        engine.dispose()

if __name__ == "__main__":
    migrate_v3_updated_at()
