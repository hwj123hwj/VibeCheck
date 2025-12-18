import re
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_init import Song, get_db_url

# 1. 初始化数据库连接
engine = create_engine(get_db_url())
Session = sessionmaker(bind=engine)
session = Session()

def get_quality_score(song):
    """
    计算歌曲质量分，分数越高越可能是“原版/正式版”
    """
    score = 100
    title = song.title.lower()
    
    # A. 负分项：标题包含明显的翻唱/次要版本词汇
    penalty_keywords = ['cover', '翻唱', 'live', '现场', '伴奏', 'instrumental', 'remix', '电音版', 'dj']
    for kw in penalty_keywords:
        if kw in title:
            score -= 50
    
    # B. 标题长度项：原版标题通常比较简洁
    # 比如 "后来" (score -2) vs "后来 (Cover 刘若英)" (score -15)
    score -= len(song.title)
    
    # C. ID 权重 (可选)：网易云早期抓取的 ID 往往更有意义
    # 这里我们只取 ID 作为最后的 TIE-BREAKER，不直接加分
    return score

def mark_duplicates():
    print("开始执行‘重复歌词’标记任务...")
    
    # 1. 先将所有歌曲重置为非重复 (以便重新计算)
    session.query(Song).update({Song.is_duplicate: False})
    session.commit()

    # 2. 找出所有重复的歌词内容
    # 使用 Python 处理分组逻辑，虽然比 SQL 慢一点点，但逻辑更可控
    from collections import defaultdict
    lyrics_map = defaultdict(list)
    
    all_songs = session.query(Song.id, Song.title, Song.lyrics).all()
    for s_id, s_title, s_lyrics in all_songs:
        if s_lyrics:
            lyrics_map[s_lyrics].append({'id': s_id, 'title': s_title})

    duplicate_groups = {lyric: group for lyric, group in lyrics_map.items() if len(group) > 1}
    
    print(f"共有 {len(duplicate_groups)} 组重复歌词，涉及 {sum(len(g) for g in duplicate_groups.values())} 首歌曲。")

    marked_count = 0
    
    for lyric, group in duplicate_groups.items():
        # 为组内每首歌打分
        # 因为 all_songs 只拿了部分字段，这里需要把对象重新构造一下或者用 lambda
        scored_group = []
        for s in group:
            # 这里的 s 是个字典
            score = get_quality_score(type('Song', (), s)) 
            scored_group.append((score, s))
        
        # 按分数从高到低排序，如果分数相同，按 ID 升序 (旧 ID 优先)
        scored_group.sort(key=lambda x: (-x[0], x[1]['id']))
        
        # 第一名保留 (is_duplicate=False)，其余全部标记为重复
        original = scored_group[0][1]
        duplicates = [x[1]['id'] for x in scored_group[1:]]
        
        if duplicates:
            session.query(Song).filter(Song.id.in_(duplicates)).update({Song.is_duplicate: True}, synchronize_session=False)
            marked_count += len(duplicates)
            # print(f"  [组内去重] 保留: {original['title']} (ID:{original['id']}), 标记重复: {len(duplicates)} 首")

    session.commit()
    print(f"全部完成！共标记了 {marked_count} 首重复/翻唱歌曲。")
    session.close()

if __name__ == "__main__":
    mark_duplicates()
