import time
import re
import requests
import random
import os
from datetime import datetime
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_init import Song, get_db_url, init_db

# ================= 配置区域 =================
TARGET_PLAYLIST_PAGES = 54  # 抓取 54 页 (每页35个，共约 1890 个歌单)
MIN_SLEEP_SECONDS = 60     # 每页抓取后最小等待时间 (秒)
MAX_SLEEP_SECONDS = 180     # 每页抓取后最大等待时间 (秒)

# 数据库连接
engine = create_engine(get_db_url())
Session = sessionmaker(bind=engine)

#反爬策略：用户代理池
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

def get_random_headers():
    return {
        "Referer": "https://music.163.com/",
        "User-Agent": random.choice(USER_AGENTS)
    }

class ServerMusicCrawler:
    def __init__(self):
        self.total_songs_saved = 0
    
    # --- Helper: 健壮的请求方法 (带重试 & 随机延时) ---
    def _safe_request(self, url, check_json=True):
        retries = 3
        for i in range(retries):
            try:
                # 随机延时，模拟人类行为 (1~3秒)
                time.sleep(random.uniform(1.0, 3.0))
                
                resp = requests.get(url, headers=get_random_headers(), timeout=15)
                
                if resp.status_code == 200:
                    if check_json:
                        return resp.json()
                    else:
                        return resp
                elif resp.status_code in [403, 503]:
                    print(f"    ! 遇到 {resp.status_code}，等待后重试 ({i+1}/{retries})...")
                    time.sleep(10 * (i + 1)) 
                else:
                    return None 
            except Exception as e:
                print(f"    ! 请求异常: {e}，重试 ({i+1}/{retries})...")
                time.sleep(5)
        return None

    # --- 核心流水线 ---
    def run_pipeline(self):
        print(f"[{datetime.now()}] === 启动长效爬虫流水线 ===")
        print(f"目标: {TARGET_PLAYLIST_PAGES} 页歌单")
        print(f"每页间隔: {MIN_SLEEP_SECONDS}-{MAX_SLEEP_SECONDS} 秒")
        
        base_url = "https://music.163.com/discover/playlist/?order=hot&cat=%E5%8D%8E%E8%AF%AD&limit=35&offset="
        
        for page in range(TARGET_PLAYLIST_PAGES):
            offset = page * 35
            url = base_url + str(offset)
            print(f"\n>>> [{datetime.now()}] 开始处理第 {page+1}/{TARGET_PLAYLIST_PAGES} 页: {url}")
            
            # 1. 抓取该页的 35 个歌单
            current_page_playlists = self._fetch_playlist_page(url)
            print(f"    - 本页成功解析 {len(current_page_playlists)} 个歌单")
            
            if not current_page_playlists:
                print("    ! 本页无数据，可能是反爬或结束，跳过...")
            else:
                # 2. 立即处理这些歌单 (抓取歌曲 & 歌词)
                self._process_playlists(current_page_playlists)
            
            # 3. 页面级长等待 (除了最后一页)
            if page < TARGET_PLAYLIST_PAGES - 1:
                sleep_time = random.randint(MIN_SLEEP_SECONDS, MAX_SLEEP_SECONDS)
                print(f"[{datetime.now()}] 本页完成，让爬虫休息 {sleep_time} 秒...")
                time.sleep(sleep_time)

    # --- Step 1 Sub-task: 抓取单页歌单 ---
    def _fetch_playlist_page(self, url):
        playlists = []
        resp = self._safe_request(url, check_json=False)
        if not resp:
            return []
        
        try:
            soup = BeautifulSoup(resp.text, 'html.parser')
            ex_ul = soup.find('ul', id='m-pl-container')
            if not ex_ul:
                print("    ! 未找到歌单容器")
                return []
            
            li_list = ex_ul.find_all('li')
            for li in li_list:
                try:
                    div = li.find('div', class_='u-cover')
                    if not div: continue
                    a_msk = div.find('a', class_='msk')
                    if not a_msk: continue
                    
                    title = a_msk.get('title')
                    href = a_msk.get('href') 
                    playlist_id = re.search(r"id=(\d+)", href).group(1)
                    playlists.append({'id': playlist_id, 'title': title})
                except:
                    pass
        except Exception as e:
            print(f"    ! 解析页面异常: {e}")
            
        return playlists

    
    # --- Step 2 & 3 Sub-task: 处理歌单列表 ---
    def _process_playlists(self, playlists):
        session = Session()
        saved_in_batch = 0
        
        total = len(playlists)
        for idx, pl in enumerate(playlists):
            playlist_id = pl['id']
            print(f"    ({idx+1}/{total}) 正在处理歌单: {pl['title']}")
            
            # 1. 获取歌单详情 (API) - 拿所有 ID
            api_url = f"https://music.163.com/api/v6/playlist/detail?id={playlist_id}"
            
            data = self._safe_request(api_url)
            if not data: continue
                
            track_ids = []
            if "playlist" in data and "trackIds" in data["playlist"]:
                track_ids = [str(t['id']) for t in data["playlist"]["trackIds"]]
            elif "playlist" in data and "tracks" in data["playlist"]:
                track_ids = [str(t['id']) for t in data["playlist"]["tracks"]]
            
            if not track_ids: continue
            
            # print(f"        -> 包含 {len(track_ids)} 首歌曲，开始分批处理...")
            
            # 2. 分批处理歌曲 (获取详情 -> 歌词 -> 入库)
            batch_size = 50
            for i in range(0, len(track_ids), batch_size):
                batch_ids = track_ids[i : i+batch_size]
                
                # A. 获取这50首的详情 (为了拿 Title 和 Artist)
                ids_param = str(batch_ids).replace("'", "")
                detail_url = f"http://music.163.com/api/song/detail?ids={ids_param}"
                
                d_data = self._safe_request(detail_url)
                if not d_data or "songs" not in d_data:
                    continue
                
                # B. 遍历这50首详情
                for track in d_data["songs"]:
                    try:
                        s_id = str(track['id'])
                        
                        # 查重 (本地数据库)
                        if session.query(Song).filter_by(id=s_id).first():
                            continue
                        
                        s_title = track['name']
                        ar_list = track.get('artists', [])
                        s_artist = "/".join([ar['name'] for ar in ar_list]) if ar_list else "Unknown"
                        
                        # 3. 抓取歌词
                        lyric_url = f"http://music.163.com/api/song/lyric?id={s_id}&lv=1&kv=1&tv=-1"
                        l_data = self._safe_request(lyric_url)
                        
                        raw_lyric = ""
                        if l_data and "lrc" in l_data and "lyric" in l_data["lrc"]:
                            raw_lyric = l_data["lrc"]["lyric"]
                        
                        # 清洗 & 过滤
                        clean_lyric = self._clean_lyric(raw_lyric)
                        if not clean_lyric or len(clean_lyric) < 10:
                            continue
                        
                        # 入库
                        new_song = Song(
                            id=s_id,
                            title=s_title,
                            artist=s_artist,
                            lyrics=clean_lyric
                        )
                        session.add(new_song)
                        saved_in_batch += 1
                        self.total_songs_saved += 1
                        
                        # 打印进度
                        if saved_in_batch % 10 == 0:
                            print(f"        -> 累计入库: {self.total_songs_saved} 首")
                            
                    except Exception as e:
                        pass
                
                # 每50首(一个batch)提交一次数据库
                session.commit()
                # time.sleep(1) # 批次间休息

        session.close()

    def _clean_lyric(self, raw):
        if not raw: return ""
        text = re.sub(r"\[\d{2}:\d{2}\.\d{2,3}\]", "", raw)
        text = re.sub(r"^.*(作词|作曲|编曲|制作|发行|混音|母带|演唱|监制|录音|吉他|贝斯|鼓).*$", "", text, flags=re.MULTILINE)
        lines = [line.strip() for line in text.split("\n") if line.strip()] 
        return "\n".join(lines)

if __name__ == "__main__":
    # 在开始前确保数据库已初始化
    try:
        init_db()
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        time.sleep(5) 
    
    bot = ServerMusicCrawler()
    # 使用流水线模式
    bot.run_pipeline()
