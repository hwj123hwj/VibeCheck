import re
from collections import Counter
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from db_init import get_db_url

engine = create_engine(get_db_url())
Session = sessionmaker(bind=engine)

def extract_chorus(lyrics, top_n=10):
    """
    通过高频探测和长度过滤提取核心内容 (Top 10)
    """
    if not lyrics:
        return ""
    
    # 1. 清洗：去掉无用空行和元信息 ([Chorus], 作词：xxx)
    lines = [line.strip() for line in lyrics.split('\n') if line.strip()]
    cleaned_lines = []
    for line in lines:
        if any(keyword in line for keyword in [":", "：", "[", "]", "作词", "作曲", "编曲", "演唱"]):
            continue
        cleaned_lines.append(line)
        
    if not cleaned_lines:
        return ""

    # 2. 统计行频
    counts = Counter(cleaned_lines)
    
    # 3. 排序策略：频次越高越优先，频次相同时字数越多越优先 (防止抓到 "Yeah" "Oh")
    # 过滤掉字数少于 5 个字的行
    sorted_lines = sorted(
        [l for l in counts if len(l) > 5], 
        key=lambda x: (counts[x], len(x)), 
        reverse=True
    )
    
    # 4. 如果没有重复行，则取歌词中间的部分
    if not sorted_lines:
        mid_start = len(cleaned_lines) // 3
        return "\n".join(cleaned_lines[mid_start:mid_start+top_n])
    
    # 5. 返回前 N 句，并按原本在歌中出现的先后顺序排好（看着更自然）
    top_lines = sorted_lines[:top_n]
    result_lines = []
    for line in cleaned_lines:
        if line in top_lines and line not in result_lines:
            result_lines.append(line)
            if len(result_lines) >= top_n:
                break
                
    return "；".join(result_lines)

def process_batch():
    session = Session()
    try:
        # 获取还没提取过精华歌词的歌 (这里假设你可能想存到一个新字段 core_lyrics)
        # 我们先打印几条测试一下
        songs = session.execute(text("SELECT id, title, lyrics FROM songs WHERE lyrics IS NOT NULL LIMIT 10")).fetchall()
        
        print(f"--- 核心歌词提取测试 ---")
        for s in songs:
            core = extract_chorus(s.lyrics)
            print(f"【{s.title}】")
            print(f"精华歌词: {core}")
            print("-" * 30)
            
    finally:
        session.close()

if __name__ == "__main__":
    process_batch()
