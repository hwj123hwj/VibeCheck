import os
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import JSONB

# Ensure you have created the database 'music_rec_db' in PostgreSQL
# and installed the extension: CREATE EXTENSION IF NOT EXISTS vector;

# Database URL
# Default user: postgres, password: password, host: localhost, port: 5432
# You might need to change this based on your local setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/music_rec_db")

Base = declarative_base()

class Song(Base):
    __tablename__ = 'songs'

    id = Column(String(50), primary_key=True, comment='Netease Song ID')
    title = Column(String(255), nullable=False)
    artist = Column(String(255), nullable=False)
    lyrics = Column(Text, comment='Original Lyrics')
    segmented_lyrics = Column(Text, comment='Segmented Lyrics for TF-IDF')
    review_text = Column(Text, comment='LLM Generated Review')
    
    # Core Vectors
    # BAAI/bge-m3 dimension is 1024
    review_vector = Column(Vector(1024), comment='Review Embedding')
    
    # TF-IDF can be stored as JSONB for sparse representation or just a list if needed.
    # Here we store as JSONB as per PRD.
    tfidf_vector = Column(JSONB, comment='TF-IDF Vector (Sparse JSON)')
    
    album_cover = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=func.now())

def init_db():
    print(f"Connecting to database at {DATABASE_URL}...")
    try:
        engine = create_engine(DATABASE_URL)
        # Create extension if not exists (needs superuser or permissions)
        # Often better to do this manually in SQL, but we can try executing SQL
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            print("Extension 'vector' ensured.")

        Base.metadata.create_all(engine)
        print("Tables created successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
        print("Tip: Make sure the database 'music_rec_db' exists.")
        print("Command: createdb -U postgres music_rec_db")

if __name__ == "__main__":
    from sqlalchemy import text
    init_db()
