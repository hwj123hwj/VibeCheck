import os
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy import create_engine, and_, func
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
    单个歌曲分析逻辑，加入频率控制和重试机制
    """
    s_id, title, artist, lyrics = song_data
    if not lyrics or len(lyrics) < 10:
        return s_id, None, "Lyrics too short"

    # 截断长歌词
    lyrics_input = lyrics[:1200]
    
    # 最多重试 3 次
    for attempt in range(3):
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
            # 成功后强制休息 3 秒，确保 RPM 安全
            time.sleep(3)
            return s_id, result, None
            
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "rate_limit" in err_msg:
                wait_time = 15 * (attempt + 1)
                print(f"  ! 触发频率限制，冷却 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                return s_id, None, err_msg
                
    return s_id, None, "Max retries reached"

def batch_process(batch_size=20, max_workers=1, daily_limit=2000):
    """
    主批处理逻辑，降速为单线程以适配 QPS 限制
    """
    from datetime import datetime, date, time as dt_time
    
    db_session = Session()
    try:
        # 0. 统计今天已经处理了多少首 (根据 updated_at 判定)
        today_start = datetime.combine(date.today(), dt_time.min)
        done_today = db_session.query(Song).filter(
            and_(
                Song.review_text != None,
                Song.updated_at >= today_start
            )
        ).count()
        
        remaining_today = daily_limit - done_today
        
        if remaining_today <= 0:
            print(f"今日任务已达成！(已完成: {done_today}/{daily_limit})。脚本自动退出。")
            return
        
        print(f"今日已完成: {done_today}/{daily_limit}，本次运行还将处理最多: {remaining_today} 首。")

        # 1. 查找待处理的歌曲
        query = db_session.query(Song.id, Song.title, Song.artist, Song.lyrics).filter(
            and_(
                Song.review_text == None,
                Song.lyrics != None,
                Song.is_duplicate == False,
                func.length(Song.lyrics) <= 1200
            )
        ).order_by(Song.created_at.desc()) # 改为倒序，先处理新抓到的
        
        total_pending = query.count()
        print(f"待处理总数: {total_pending}")

        processed_this_run = 0
        while processed_this_run < remaining_today:
            # 单线程模式下 batch 不需要太大
            current_batch_limit = min(batch_size, remaining_today - processed_this_run)
            batch_songs = query.limit(current_batch_limit).all()
            
            if not batch_songs:
                print("所有待处理歌曲已全部完成！")
                break
            
            print(f"\n>>> 正在一首一首分析 (今日进度: {done_today + processed_this_run + 1}/{daily_limit})...")
            
            # 虽然设为了单线程，但保留 ThreadPoolExecutor 结构方便后续你提升权限后再改回来
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(analyze_single_song, song): song for song in batch_songs}
                
                for future in as_completed(futures):
                    s_id, result, error = future.result()
                    if error:
                        print(f"  ! 歌曲 {s_id} 处理跳过: {error}")
                    else:
                        try:
                            update_session = Session()
                            update_session.query(Song).filter(Song.id == s_id).update({
                                Song.vibe_tags: result.get('vibe_tags'),
                                Song.vibe_scores: result.get('emotional_scores'),
                                Song.review_text: result.get('review'),
                                Song.recommend_scene: result.get('scene'),
                                Song.updated_at: datetime.now()
                            })
                            update_session.commit()
                            update_session.close()
                            # print(f"  √ {s_id} OK")
                        except Exception as inner_e:
                            print(f"  ! 数据库写入失败 {s_id}: {inner_e}")
            
            processed_this_run += len(batch_songs)

        if processed_this_run >= remaining_today:
            print(f"\n已触及今日限额 ({daily_limit} 首)，脚本安全停止。")

    finally:
        db_session.close()

if __name__ == "__main__":
    # 改为单线程稳健模式，每日上限调至 3000 首
    batch_process(batch_size=10, max_workers=1, daily_limit=3000)
