import re
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_init import Song, get_db_url

# 1. 初始化数据库连接
engine = create_engine(get_db_url())
Session = sessionmaker(bind=engine)
session = Session()

def clean_title(title):
    """
    标题仅清洗 NBSP (\xa0)
    """
    if not title:
        return ""
    # 将 NBSP 替换为标准空格，并去除两端空格
    return title.replace('\xa0', ' ').strip()

def clean_lyrics(text):
    """
    歌词清洗：处理 NBSP，并移除干扰元数据行
    """
    if not text:
        return ""
    
    # A. 替换 NBSP 为标准空格
    text = text.replace('\xa0', ' ').replace('\u3000', ' ')
    
    # B. 移除各种格式的时间轴：[00:25.0], [01:59], [01:59][00:15] 等
    text = re.sub(r'\[\d+:\d+(?:\.\d+)?\]', '', text)
    
    # C. 定义无效行关键词模式 (支持模糊匹配和常见空格变体)
    junk_keywords = [
        r'作\s*词', r'作\s*曲', r'填\s*词', r'编\s*曲', r'监\s*制', r'制\s*作', 
        r'录\s*音', r'混\s*音', r'吉\s*他', r'贝\s*斯', r'鼓', r'键\s*盘', 
        r'弦\s*乐', r'和\s*声', r'合\s*声', r'艺人统筹', r'宣\s*发', r'封\s*面', 
        r'后期', r'出品', r'发行', r'音响总监', r'实\s*录', r'二\s*胡', 
        r'笛\s*子', r'钢琴', r'小提琴', r'大提琴', r'古筝', r'琵琶', 
        r'策\s*划', r'曲\s*绘', r'视\s*频', r'视\s*觉', r'录\s*混', r'营\s*销', 
        r'原\s*唱', r'音乐总监', r'BandLeader', r'打击乐', r'和\s*音',
        r'词', r'曲', r'Mix', r'Mastering', r'Arrangement', r'Producer', 
        r'Bass', r'Guitar', r'Piano', r'Drums', r'Strings', r'Program',
        r'OP', r'SP', r'Provided', r'Licensed', r'Technician', r'Director',
        r'Produced', r'PV', r'Vocal'
    ]
    
    # 构造正则表达式：匹配包含关键词且后面紧跟冒号、等号或多量空格的行
    # 注意：使用 \s*[:：\s=] 确保匹配到分隔符，防止误删正常歌词
    junk_pattern = re.compile(
        r'^\s*(?:' + '|'.join(junk_keywords) + r')\s*[:：\s=].*$', 
        re.IGNORECASE
    )
    
    lines = text.split('\n')
    clean_lines = []
    
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
            
        # 排除掉包含噪音关键词的行
        if junk_pattern.match(stripped):
            continue
            
        # 排除掉一些太短且没意义的行（可选，这里先保留文字内容）
        if len(stripped) <= 1 and not stripped.isalnum():
            continue
            
        clean_lines.append(stripped)
        
    return '\n'.join(clean_lines)

def run_cleaning():
    print("开始执行存量数据清洗任务...")
    
    # 一次性获取所有歌曲 ID (避免长时间占住结果集)
    all_songs = session.query(Song).all()
    total = len(all_songs)
    print(f"共有 {total} 首歌曲等待处理。")
    
    count = 0
    updated_count = 0
    
    start_time = time.time()
    
    for song in all_songs:
        original_title = song.title
        original_lyrics = song.lyrics
        
        new_title = clean_title(original_title)
        new_lyrics = clean_lyrics(original_lyrics)
        
        # 检查是否有变化，减少无效更新
        if new_title != original_title or new_lyrics != original_lyrics:
            song.title = new_title
            song.lyrics = new_lyrics
            updated_count += 1
            
        count += 1
        
        # 每 1000 条提交一次，防止事务过大
        if count % 1000 == 0:
            session.commit()
            elapsed = time.time() - start_time
            print(f"进度: {count}/{total} (已更新: {updated_count}), 耗时: {elapsed:.2f}s")
            
    session.commit()
    print(f"全部完成！共扫描 {total} 首，更新了 {updated_count} 首。")
    session.close()

if __name__ == "__main__":
    run_cleaning()
