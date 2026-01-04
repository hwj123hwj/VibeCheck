import time
import re
import requests
import random
from datetime import datetime
from bs4 import BeautifulSoup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_init import Song, get_db_url

# ================= 配置区域 =================
# ================= 配置区域 =================
TARGET_PLAYLIST_PAGES = 2  # 抓取 2 页 (约 70 个歌单)，覆盖 54 个的需求

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
        self.playlists = [] 
        self.songs_meta = {} 
    
    # --- Helper: 健壮的请求方法 (带重试 & 随机延时) ---
    def _safe_request(self, url, check_json=True):
        retries = 3
        for i in range(retries):
            try:
                # 随机延时，模拟人类行为 (1~3秒)
                time.sleep(random.uniform(1.0, 3.0))
                
                resp = requests.get(url, headers=get_random_headers(), timeout=10)
                
                if resp.status_code == 200:
                    if check_json:
                        # 尝试解析 JSON 验证有效性
                        return resp.json()
                    else:
                        return resp
                elif resp.status_code in [403, 503]:
                    print(f"    ! 遇到 {resp.status_code}，等待后重试 ({i+1}/{retries})...")
                    time.sleep(5 * (i + 1)) # 指数退避
                else:
                    return None # 其他错误不重试
            except Exception as e:
                print(f"    ! 请求异常: {e}，重试 ({i+1}/{retries})...")
                time.sleep(2)
        return None

    # --- Step 1: 抓取歌单列表 (Requests + BS4) ---
    def fetch_playlists(self):
        print(f"[{datetime.now()}] === Step 1: 开始抓取歌单列表 (Requests - 华语) ===")
        
        base_url = "https://music.163.com/discover/playlist/?order=hot&cat=%E5%8D%8E%E8%AF%AD&limit=35&offset="
        
        for page in range(TARGET_PLAYLIST_PAGES):
            offset = page * 35
            url = base_url + str(offset)
            print(f"  正在抓取第 {page+1} 页: {url}")
            
            resp = self._safe_request(url, check_json=False)
            if not resp:
                print("    ! 页面抓取失败，跳过")
                continue
            
            try:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                ex_ul = soup.find('ul', id='m-pl-container')
                if not ex_ul:
                    print("    ! 未找到歌单列表容器 (m-pl-container)")
                    continue
                
                li_list = ex_ul.find_all('li')
                print(f"    - 找到 {len(li_list)} 个歌单")
                
                for li in li_list:
                    try:
                        div = li.find('div', class_='u-cover')
                        if not div: continue
                        
                        a_msk = div.find('a', class_='msk')
                        if not a_msk: continue
                        
                        title = a_msk.get('title')
                        href = a_msk.get('href') 
                        
                        playlist_id = re.search(r"id=(\d+)", href).group(1)
                        self.playlists.append({'id': playlist_id, 'title': title})
                        
                    except Exception as e:
                        pass
                        
            except Exception as e:
                print(f"    ! 解析异常: {e}")
            
        print(f"  Step 1 完成: 共获取 {len(self.playlists)} 个歌单。")

    
    def fetch_songs_and_save(self):
        print(f"[{datetime.now()}] === Step 2 & 3: 遍历歌单 -> 抓取歌曲 -> 存入数据库 ===")
        
        session = Session()
        total_saved = 0
        
        for idx_pl, pl in enumerate(self.playlists):
            playlist_id = pl['id']
            print(f"  处理歌单 [{idx_pl+1}/{len(self.playlists)}]: {pl['title']}")
            
            # 1. 获取歌单详情 (API)
            api_url = f"https://music.163.com/api/v6/playlist/detail?id={playlist_id}"
            
            data = self._safe_request(api_url)
            if not data:
                print("    ! 获取歌单详情失败")
                continue
                
            tracks = []
            if "playlist" in data and "tracks" in data["playlist"]:
                tracks = data["playlist"]["tracks"]
            
            # 2. 遍历歌曲
            for track in tracks:
                try:
                    s_id = str(track['id'])
                    
                    # 查重 (本地数据库)
                    if session.query(Song).filter_by(id=s_id).first():
                        continue
                    
                    s_title = track['name']
                    ar_list = track.get('ar', [])
                    s_artist = "/".join([ar['name'] for ar in ar_list]) if ar_list else "Unknown"
                    
                    # 3. 抓取歌词
                    lyric_url = f"http://music.163.com/api/song/lyric?id={s_id}&lv=1&kv=1&tv=-1"
                    l_data = self._safe_request(lyric_url)
                    
                    raw_lyric = ""
                    if l_data and "lrc" in l_data and "lyric" in l_data["lrc"]:
                        raw_lyric = l_data["lrc"]["lyric"]
                    
                    # 4. 清洗
                    clean_lyric = self._clean_lyric(raw_lyric)
                    
                    # 5. 过滤
                    if not clean_lyric or len(clean_lyric) < 10:
                        continue
                    
                    # 6. 入库
                    new_song = Song(
                        id=s_id,
                        title=s_title,
                        artist=s_artist,
                        lyrics=clean_lyric
                    )
                    session.add(new_song)
                    total_saved += 1
                    
                    if total_saved % 20 == 0:
                        session.commit()
                        print(f"    ... 已累计入库 {total_saved} 首")
                        
                except Exception as e:
                    pass
            
            session.commit() # 每个歌单保存一次
                
        session.close() # End of loop
        print(f"[{datetime.now()}] === 全部完成，共新增 {total_saved} 首歌曲 ===")

    def _clean_lyric(self, raw):
        if not raw: return ""
        text = re.sub(r"\[\d{2}:\d{2}\.\d{2,3}\]", "", raw)
        text = re.sub(r"^.*(作词|作曲|编曲|制作|发行|混音|母带|演唱|监制|录音|吉他|贝斯|鼓).*$", "", text, flags=re.MULTILINE)
        lines = [line.strip() for line in text.split("\n") if line.strip()] 
        return "\n".join(lines)

if __name__ == "__main__":
    bot = ServerMusicCrawler()
    bot.fetch_playlists()
    if bot.playlists:
        bot.fetch_songs_and_save()
