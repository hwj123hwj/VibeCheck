import os
import time
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func, JSON, text
from sqlalchemy.orm import declarative_base, sessionmaker
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import ProgrammingError

# 数据库配置
# ⚠️ 注意：运行在本地 Docker 容器中，端口映射为 5433
DB_CONFIG = {
    "user": "root",
    "password": "15671040800q",
    "host": "127.0.0.1",
    "port": "5433", 
    "database": "music_db"
}

# 构建数据库连接 URL
def get_db_url(dbname=None):
    if dbname is None:
        dbname = DB_CONFIG["database"]
    return f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{dbname}"

Base = declarative_base()

class Song(Base):
    __tablename__ = 'songs'

    id = Column(String(50), primary_key=True, comment='网易云音乐歌曲ID')
    title = Column(String(255), nullable=False, comment='歌曲标题')
    artist = Column(String(255), nullable=False, comment='歌手')
    lyrics = Column(Text, comment='原始歌词')
    segmented_lyrics = Column(Text, comment='分词后的歌词 (用于 TF-IDF)')
    review_text = Column(Text, comment='LLM 生成的情感评语')
    
    # 核心向量字段
    # BAAI/bge-m3 output dimension is 1024
    review_vector = Column(Vector(1024), comment='评语 Embedding 向量')
    
    # TF-IDF 向量 (使用 JSONB 存储稀疏矩阵或索引)
    tfidf_vector = Column(JSONB, comment='TF-IDF 向量 (JSON)')
    
    album_cover = Column(String(500), nullable=True, comment='专辑封面 URL')
    created_at = Column(DateTime, default=func.now(), comment='创建时间')

def create_database_if_not_exists():
    """
    如果数据库不存在，连接到默认的 'postgres' 数据库并创建目标数据库。
    """
    # 先连接到默认的 postgres 数据库
    default_url = get_db_url("postgres")
    engine = create_engine(default_url, isolation_level="AUTOCOMMIT")
    
    target_db = DB_CONFIG["database"]
    
    try:
        with engine.connect() as conn:
            # 检查数据库是否存在
            result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{target_db}'"))
            if not result.fetchone():
                print(f"数据库 '{target_db}' 不存在，正在创建...")
                conn.execute(text(f"CREATE DATABASE {target_db}"))
                print(f"数据库 '{target_db}' 创建成功。")
            else:
                print(f"数据库 '{target_db}' 已存在。")
    except Exception as e:
        print(f"检查或创建数据库时出错: {e}")
        raise

def init_db():
    # 1. 确保存储库存在
    create_database_if_not_exists()
    
    # 2. 连接到目标数据库
    target_url = get_db_url()
    print(f"正在连接到数据库: {target_url} ...")
    engine = create_engine(target_url)
    
    try:
        with engine.connect() as conn:
            # 启用 vector 插件 (需要超级用户权限，Docker 容器中的 root 用户通常有此权限)
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            print("已启用 'vector' 扩展。")

        # 创建表结构
        Base.metadata.create_all(engine)
        print("表结构创建成功。")
    except Exception as e:
        print(f"初始化数据库表时出错: {e}")

if __name__ == "__main__":
    init_db()
