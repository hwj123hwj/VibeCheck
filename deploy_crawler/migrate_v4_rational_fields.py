from sqlalchemy import create_engine, text
from db_init import get_db_url

def migrate_v4_rational_fields():
    engine = create_engine(get_db_url())
    try:
        with engine.connect() as conn:
            # 需要添加的字段
            new_columns = [
                ("segmented_lyrics", "TEXT"),
                ("tfidf_vector", "JSONB"),
                ("review_vector", "vector(1024)") # 如果 pgvector 插件已开启
            ]
            
            for col_name, col_type in new_columns:
                # 检查列是否存在
                check_sql = f"SELECT 1 FROM information_schema.columns WHERE table_name='songs' AND column_name='{col_name}'"
                result = conn.execute(text(check_sql)).fetchone()
                
                if not result:
                    print(f"正在向 'songs' 表添加 '{col_name}' 字段...")
                    try:
                        conn.execute(text(f"ALTER TABLE songs ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                        print(f"字段 '{col_name}' 添加成功。")
                    except Exception as col_e:
                        print(f"添加字段 '{col_name}' 失败: {col_e}")
                else:
                    print(f"字段 '{col_name}' 已存在。")
                    
    except Exception as e:
        print(f"迁移时出错: {e}")
    finally:
        engine.dispose()

if __name__ == "__main__":
    migrate_v4_rational_fields()
