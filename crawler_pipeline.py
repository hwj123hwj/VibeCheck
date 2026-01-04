import time
import re
import requests
import csv
import os
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_init import Song, get_db_url

# ================= 配置区域 =================
# 目标抓取歌单数量 (每页35个，2页即70个，54个需要抓2页)
TARGET_PLAYLIST_PAGES = 2 

# 数据库连接 (确保 DB_CONFIG 配置正确)
engine = create_engine(get_db_url())
Session = sessionmaker(bind=engine)

# 请求头
HEADERS = {
    "Referer": "https://music.163.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

# ================= 核心类 =================
class MusicCrawlerPipeline:
    def __init__(self):
        self.playlists = [] # stores {'id':, 'title':}
        self.songs_meta = {} # stores song_id -> {'title', 'artist'}
    
    # --- Step 1: 抓取歌单列表 (Selenium) ---
    def fetch_playlists(self):
        print(f"[{datetime.now()}] === Step 1: 开始抓取歌单列表 (Hot - 华语) ===")
        
        chrome_options = Options()
        chrome_options.add_argument("--headless") # 服务器模式通常需要 headless
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument(f"user-agent={HEADERS['User-Agent']}")
        
        driver = webdriver.Chrome(options=chrome_options)
        base_url = "https://music.163.com/discover/playlist/?order=hot&cat=%E5%8D%8E%E8%AF%AD&limit=35&offset="
        
        try:
            for page in range(TARGET_PLAYLIST_PAGES):
                offset = page * 35
                url = base_url + str(offset)
                print(f"  正在抓取第 {page+1} 页: {url}")
                
                try:
                    driver.get(url)
                    time.sleep(3)
                    driver.switch_to.frame("g_iframe")
                    
                    xpath = "//div[@id='m-disc-pl-c']/div/ul[@id='m-pl-container']/li"
                    li_list = driver.find_elements(By.XPATH, xpath)
                    
                    print(f"    - 找到 {len(li_list)} 个歌单")
                    
                    for li in li_list:
                        try:
                            a_tag = li.find_element(By.XPATH, ".//div/a[@class='msk']")
                            title = a_tag.get_attribute("title")
                            href = a_tag.get_attribute("href")
                            playlist_id = re.search(r"id=(\d+)", href).group(1)
                            
                            self.playlists.append({'id': playlist_id, 'title': title})
                        except Exception as e:
                            pass
                            
                except Exception as e:
                    print(f"    ! 抓取页面失败: {e}")
                    
        finally:
            driver.quit()
            
        print(f"  Step 1 完成: 共获取 {len(self.playlists)} 个歌单。")

    # --- Step 2: 抓取歌曲元数据 (API) ---
    def fetch_songs_meta(self):
        print(f"[{datetime.now()}] === Step 2: 开始从歌单抓取歌曲 ID ===")
        
        total_pl = len(self.playlists)
        for idx, pl in enumerate(self.playlists):
            playlist_id = pl['id']
            print(f"  [{idx+1}/{total_pl}] 处理歌单: {pl['title']}")
            
            url = f"https://music.163.com/api/v6/playlist/detail?id={playlist_id}"
            
            try:
                resp = requests.get(url, headers=HEADERS, timeout=10)
                data = resp.json()
                
                if "playlist" in data and "tracks" in data["playlist"]:
                    tracks = data["playlist"]["tracks"]
                    # print(f"    - 包含 {len(tracks)} 首歌曲")
                    
                    for track in tracks:
                        try:
                            s_id = str(track['id'])
                            # 去重
                            if s_id in self.songs_meta:
                                continue
                                
                            s_title = track['name']
                            ar_list = track.get('ar', [])
                            s_artist = "/".join([ar['name'] for ar in ar_list]) if ar_list else "Unknown"
                            
                            self.songs_meta[s_id] = {
                                "id": s_id,
                                "title": s_title,
                                "artist": s_artist
                            }
                        except:
                            pass
                
                time.sleep(random.uniform(0.5, 1.0)) # 避免触发风控
                
            except Exception as e:
                print(f"    ! 歌单抓取失败: {e}")
                
        print(f"  Step 2 完成: 共收集 {len(self.songs_meta)} 首唯一歌曲元数据。")

    # --- Step 3: 抓取歌词并入库 (API -> DB) ---
    def fetch_lyrics_and_save(self):
        print(f"[{datetime.now()}] === Step 3: 开始抓取歌词并存入数据库 ===")
        
        session = Session()
        songs_list = list(self.songs_meta.values())
        total_songs = len(songs_list)
        
        success_count = 0
        skip_count = 0
        
        for idx, s in enumerate(songs_list):
            s_id = s["id"]
            
            # 1. 查重 (数据库)
            if session.query(Song).filter_by(id=s_id).first():
                skip_count += 1
                if idx % 50 == 0:
                    print(f"  [{idx+1}/{total_songs}] 跳过已存在 ({s['title']})")
                continue
            
            # 2. 抓取歌词
            raw_lyric = self._get_lyric_api(s_id)
            clean_lyric = self._clean_lyric(raw_lyric)
            
            # 3. 过滤无效歌词
            if not clean_lyric or len(clean_lyric) < 10:
                print(f"  [{idx+1}/{total_songs}] 无有效歌词，跳过: {s['title']}")
                continue
            
            # 4. 入库
            new_song = Song(
                id=s_id,
                title=s["title"],
                artist=s["artist"],
                lyrics=clean_lyric
            )
            session.add(new_song)
            success_count += 1
            print(f"  [{idx+1}/{total_songs}] 入库: {s['title']}")
            
            # 批量提交
            if success_count % 20 == 0:
                session.commit()
            
            time.sleep(0.2)
            
        session.commit()
        session.close()
        print(f"[{datetime.now()}] === 全部完成 ===")
        print(f"  总结: 总歌曲 {total_songs}, 新增入库 {success_count}, 数据库已存在跳过 {skip_count}")

    # Helper: 获取歌词
    def _get_lyric_api(self, song_id):
        url = f"http://music.163.com/api/song/lyric?id={song_id}&lv=1&kv=1&tv=-1"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=5)
            data = resp.json()
            if "lrc" in data and "lyric" in data["lrc"]:
                return data["lrc"]["lyric"]
        except:
            pass
        return ""

    # Helper: 清洗歌词
    def _clean_lyric(self, raw):
        if not raw: return ""
        text = re.sub(r"\[\d{2}:\d{2}\.\d{2,3}\]", "", raw)
        text = re.sub(r"^.*(作词|作曲|编曲|制作|发行|混音|母带|演唱|监制|录音|吉他|贝斯|鼓).*$", "", text, flags=re.MULTILINE)
        lines = [line.strip() for line in text.split("\n") if line.strip()] 
        return "\n".join(lines)

    # --- 主入口 ---
    def run(self):
        # 1. 抓取歌单
        self.fetch_playlists()
        
        # 2. 抓取歌曲元数据
        if self.playlists:
            self.fetch_songs_meta()
        else:
            print("未获取到歌单，终止。")
            return
            
        # 3. 抓取歌词并入库
        if self.songs_meta:
            self.fetch_lyrics_and_save()
        else:
            print("未获取到歌曲，终止。")

if __name__ == "__main__":
    crawler = MusicCrawlerPipeline()
    crawler.run()
