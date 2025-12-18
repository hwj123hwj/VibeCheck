import os
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import create_engine, and_
from sqlalchemy.orm import sessionmaker
from db_init import Song, get_db_url

# 1. 加载环境变量
load_dotenv()
api_key = os.getenv("LONGMAO_API_KEY")
base_url = os.getenv("LONGMAO_BASE_URL")
model_name = os.getenv("LONGMAO_MODEL")

if not api_key:
    raise ValueError("未找到 LONGMAO_API_KEY，请检查 .env 文件")

client = OpenAI(api_key=api_key, base_url=base_url)

# 2. 数据库连接
engine = create_engine(get_db_url())
Session = sessionmaker(bind=engine)

# 3. Prompt 模板
prompt_template = """
你是一位天才音乐评论家和情感心理专家。请阅读以下歌词，并进行深度的意境分析。

歌曲标题: {title}
歌手: {artist}
歌词内容:
{lyrics}

---
请输出 JSON 格式的结构化分析结果，包含以下字段：
1. vibe_tags: 3-5个意境标签（如：深夜、雨夜、初恋、孤独、治愈等）。
2. emotional_scores: 包含以下维度的评分（0.0-1.0）：
   - loneliness (孤独感)
   - energy (能量感/热烈度)
   - healing (治愈感)
   - nostalgic (怀旧感)
   - sorrow (表现伤感程度)
3. review: 一段100字左右的高级评语。要求：富有诗意，能精准捕捉歌词中的情感内核。
4. scene: 适合收听这首歌的场景描述。

注意：只输出纯 JSON 格式，不要包含任何 markdown 标记。
"""

def analyze_single_song(song_data):
    """
    单个歌曲分析逻辑
    """
    s_id, title, artist, lyrics = song_data
    if not lyrics or len(lyrics) < 10:
        return s_id, None, "Lyrics too short"

    # 截断长歌词
    lyrics_input = lyrics[:1200]
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "你是一个专业的音乐情感分析引擎，只输出 JSON。"},
                {"role": "user", "content": prompt_template.format(
                    title=title,
                    artist=artist,
                    lyrics=lyrics_input
                )}
            ],
            temperature=0.7,
            response_format={ "type": "json_object" }
        )
        
        result = json.loads(response.choices[0].message.content)
        return s_id, result, None
    except Exception as e:
        return s_id, None, str(e)

def batch_process(batch_size=10, max_workers=5):
    """
    主批处理逻辑
    """
    db_session = Session()
    try:
        # 查找未处理的歌曲 (review_text 为空且不是重复歌曲)
        # 注意：如果您想处理重复歌曲，可以去掉 is_duplicate 过滤
        query = db_session.query(Song.id, Song.title, Song.artist, Song.lyrics).filter(
            and_(
                Song.review_text == None,
                Song.lyrics != None,
                Song.is_duplicate == False
            )
        )
        
        total_count = query.count()
        print(f"开始批量 AI 分析任务，待处理歌曲总数: {total_count}")
        
        if total_count == 0:
            print("没有运行任务的必要，所有歌曲已处理完毕。")
            return

        # 每次取出一批进行处理，避免内存占用过大
        processed_total = 0
        while True:
            batch_songs = query.limit(batch_size).all()
            if not batch_songs:
                break
            
            print(f"\n>>> 正在处理批次 ({processed_total}/{total_count})...")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(analyze_single_song, song): song for song in batch_songs}
                
                for future in as_completed(futures):
                    s_id, result, error = future.result()
                    if error:
                        print(f"  ! 歌曲 {s_id} 处理失败: {error}")
                        # 如果失败，我们可以给它打个标记避免死循环，或者直接跳过
                        # 这里简单处理：暂时不更新数据库，下次还会查出来
                    else:
                        # 更新数据库
                        try:
                            # 开启一个新的 session 执行更新，防止主查询 session 冲突
                            update_session = Session()
                            song_obj = update_session.query(Song).get(s_id)
                            song_obj.vibe_tags = result.get('vibe_tags')
                            song_obj.vibe_scores = result.get('emotional_scores')
                            song_obj.review_text = result.get('review')
                            song_obj.recommend_scene = result.get('scene')
                            update_session.commit()
                            update_session.close()
                            # print(f"  √ 歌曲 {s_id} 分析完成")
                        except Exception as inner_e:
                            print(f"  ! 数据库持久化失败 {s_id}: {inner_e}")
            
            processed_total += len(batch_songs)
            # 适当休眠，保护 API 频率
            time.sleep(1)

    finally:
        db_session.close()

if __name__ == "__main__":
    # 配置：每次取 20 首，5个线程并发
    # 500w token 每天大约能跑 5000-8000 首（取决于歌词长度）
    batch_process(batch_size=20, max_workers=5)
