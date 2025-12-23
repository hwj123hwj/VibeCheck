import jieba
import re
from sqlalchemy import create_engine, and_, text
from sqlalchemy.orm import sessionmaker
from sklearn.feature_extraction.text import TfidfVectorizer
import json
from db_init import Song, get_db_url

# 1. 初始化数据库连接
engine = create_engine(get_db_url())
Session = sessionmaker(bind=engine)

def clean_text(text):
    """
    清洗文本，仅保留中文字符
    """
    if not text:
        return ""
    # 移除非中文字符（可选，根据需求保留英文/数字）
    return "".join(re.findall(r'[\u4e00-\u9fa5]+', text))

def segment_all_songs():
    """
    第一阶段：对所有未分词的歌词进行分词
    """
    session = Session()
    try:
        # 查找有歌词但未分词的歌
        songs = session.query(Song).filter(
            and_(
                Song.lyrics != None,
                Song.segmented_lyrics == None,
                Song.is_duplicate == False
            )
        ).all()
        
        print(f"找到 {len(songs)} 首待分词歌曲...")
        
        for i, song in enumerate(songs):
            content = clean_text(song.lyrics)
            if content:
                # 使用 jieba 精确模式分词
                seg_list = jieba.cut(content)
                song.segmented_lyrics = " ".join(seg_list)
            else:
                song.segmented_lyrics = ""
                
            if (i + 1) % 100 == 0:
                session.commit()
                print(f"已分词: {i + 1}/{len(songs)}")
                
        session.commit()
        print("分词阶段全部完成。")
    finally:
        session.close()

def compute_and_save_tfidf(top_n=10):
    """
    第二阶段：基于全量分词结果计算 TF-IDF 并提取关键词
    """
    session = Session()
    try:
        # 获取所有已分词且非重复的歌曲
        songs = session.query(Song).filter(
            and_(
                Song.segmented_lyrics != None,
                Song.segmented_lyrics != "",
                Song.is_duplicate == False
            )
        ).all()
        
        if not songs:
            print("没有找到已分词的歌曲，请先执行分词阶段。")
            return

        corpus = [s.segmented_lyrics for s in songs]
        song_ids = [s.id for s in songs]
        
        print(f"正在计算 {len(corpus)} 首歌曲的 TF-IDF 矩阵...")
        
        # 定义 TF-IDF 向量化器
        # max_df=0.9: 过滤掉在 90% 以上文档中出现的词
        # min_df=2: 过滤掉只在 1 个文档中出现的词
        vectorizer = TfidfVectorizer(max_df=0.9, min_df=2, max_features=20000)
        tfidf_matrix = vectorizer.fit_transform(corpus)
        
        # 获取词表
        feature_names = vectorizer.get_feature_names_out()
        
        print("提取并保存每个文档的关键词...")
        for i, s_id in enumerate(song_ids):
            # 获取当前文档的 TF-IDF 向量
            row = tfidf_matrix.getrow(i)
            # 排序获取权重最高的词
            sorted_items = sorted(zip(row.indices, row.data), key=lambda x: x[1], reverse=True)
            
            # 提取 Top N 关键词
            keywords = {}
            for idx, score in sorted_items[:top_n]:
                word = feature_names[idx]
                keywords[word] = round(float(score), 4)
            
            # 更新到数据库
            session.query(Song).filter(Song.id == s_id).update({
                Song.tfidf_vector: keywords
            })
            
            if (i + 1) % 500 == 0:
                session.commit()
                print(f"已保存关键词: {i + 1}/{len(song_ids)}")
                
        session.commit()
        print("TF-IDF 关键词处理完毕。")
    finally:
        session.close()

if __name__ == "__main__":
    print("开始分词阶段...")
    segment_all_songs()
    print("\n开始计算 TF-IDF 阶段...")
    compute_and_save_tfidf()
