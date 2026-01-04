import time
import re
import requests
import csv
import os
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_init import Song, get_db_url

# 数据库连接
engine = create_engine(get_db_url())
Session = sessionmaker(bind=engine)

class NetCloudCrawler:
    def __init__(self):
        print("初始化爬虫...")
        chrome_options = Options()
        # chrome_options.add_argument("--headless") 
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        # 伪装 User-Agent
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")
        
        # 延迟初始化 driver，只有需要 Selenium 的步骤才启动
        self.chrome_options = chrome_options
        self.driver = None
        self.session = Session()

    def start_driver(self):
        if not self.driver:
            self.driver = webdriver.Chrome(options=self.chrome_options)

    def close_driver(self):
        if self.driver:
            self.driver.quit()
            self.driver = None

    # Step 1: 爬取歌单 ID -> playlists.csv
    def step1_fetch_playlists(self, max_pages=2):
        print("=== Step 1: 开始爬取热门歌单列表 ===")
        self.start_driver()
        playlists = []
        base_url = "https://music.163.com/discover/playlist/?order=hot&cat=%E5%85%A8%E9%83%A8&limit=35&offset="
        
        for page in range(max_pages):
            offset = page * 35
            url = base_url + str(offset)
            print(f"Fetch URL: {url}")
            
            try:
                self.driver.get(url)
                time.sleep(3)
                self.driver.switch_to.frame("g_iframe")
                
                xpath = "//div[@id='m-disc-pl-c']/div/ul[@id='m-pl-container']/li"
                li_list = self.driver.find_elements(By.XPATH, xpath)
                
                print(f"Page {page+1}: 找到 {len(li_list)} 个歌单")
                
                for li in li_list:
                    try:
                        a_tag = li.find_element(By.XPATH, ".//div/a[@class='msk']")
                        title = a_tag.get_attribute("title")
                        href = a_tag.get_attribute("href")
                        playlist_id = re.search(r"id=(\d+)", href).group(1)
                        
                        playlists.append([playlist_id, title, href])
                    except Exception as e:
                        print(f"Error parsing playlist: {e}")
            except Exception as e:
                print(f"Error on page {page}: {e}")
        
        self.close_driver()
        
        # 保存到 csv
        with open("playlists.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "title", "url"])
            writer.writerows(playlists)
        print(f"Step 1 完成: 已保存 {len(playlists)} 个歌单到 playlists.csv")

    # Step 2: 读取 playlists.csv -> 爬取歌曲 ID -> songs_meta.csv
    def step2_fetch_songs_IDs(self):
        print("=== Step 2: 开始从歌单爬取歌曲 ID ===")
        if not os.path.exists("playlists.csv"):
            print("错误: 找不到 playlists.csv，请先运行 Step 1")
            return

        self.start_driver()
        
        # 读取歌单
        playlists = []
        with open("playlists.csv", "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                playlists.append(row)

        all_songs = {} # 使用 dict 去重: song_id -> {meta}
        
        for idx, pl in enumerate(playlists):
            print(f"[{idx+1}/{len(playlists)}] 处理歌单: {pl['title']}")
            url = f"https://music.163.com/playlist?id={pl['id']}"
            
            try:
                self.driver.get(url)
                time.sleep(2)
                self.driver.switch_to.frame("g_iframe")
                
                rows = self.driver.find_elements(By.XPATH, "//table[@class='m-table']/tbody/tr")
                print(f"  - 发现 {len(rows)} 首歌曲")

                for row in rows:
                    try:
                        txt_span = row.find_element(By.CSS_SELECTOR, "span.txt")
                        a_tag = txt_span.find_element(By.TAG_NAME, "a")
                        href = a_tag.get_attribute("href")
                        song_id = re.search(r"id=(\d+)", href).group(1)
                        song_title = a_tag.find_element(By.TAG_NAME, "b").get_attribute("title")

                        # 歌手信息 (第4列)
                        artist = "Unknown"
                        try:
                            tds = row.find_elements(By.TAG_NAME, "td")
                            if len(tds) > 3:
                                artist_div = tds[3].find_element(By.CSS_SELECTOR, "div.text")
                                artist = artist_div.get_attribute("title")
                        except:
                            pass

                        # 存入字典去重
                        if song_id not in all_songs:
                            all_songs[song_id] = {
                                "id": song_id,
                                "title": song_title,
                                "artist": artist
                            }
                    except:
                        pass
                
                time.sleep(1) # 礼貌等待
                
            except Exception as e:
                print(f"Error fetching playlist {pl['id']}: {e}")

        self.close_driver()
        
        # 保存歌曲元数据
        with open("songs_meta.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "title", "artist"])
            for sid, meta in all_songs.items():
                writer.writerow([meta["id"], meta["title"], meta["artist"]])
                
        print(f"Step 2 完成: 已保存 {len(all_songs)} 首去重歌曲到 songs_meta.csv")

    # Step 3: 读取 songs_meta.csv -> API 抓取歌词 -> 存入数据库
    def step3_fetch_lyrics_and_save(self):
        print("=== Step 3: 抓取歌词并存入数据库 ===")
        if not os.path.exists("songs_meta.csv"):
            print("错误: 找不到 songs_meta.csv，请先运行 Step 2")
            return
        
        songs_list = []
        with open("songs_meta.csv", "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                songs_list.append(row)
        
        print(f"待处理歌曲总数: {len(songs_list)}")
        
        count = 0
        success_count = 0
        
        for s in songs_list:
            count += 1
            song_id = s["id"]
            
            # 1. 检查数据库是否已存在
            exists = self.session.query(Song).filter_by(id=song_id).first()
            if exists:
                # print(f"[{count}] 跳过已存在: {s['title']}")
                continue
            
            # 2. 调用 API 获取歌词 (无需 Selenium)
            raw_lyric = self._api_fetch_lyric(song_id)
            clean_lyric = self._clean_lyrics(raw_lyric)
            
            # 过滤掉无歌词或纯音乐
            if not clean_lyric or len(clean_lyric) < 20:
                print(f"[{count}] 无有效歌词，跳过: {s['title']}")
                continue
            
            # 3. 入库
            new_song = Song(
                id=song_id,
                title=s["title"],
                artist=s["artist"],
                lyrics=clean_lyric
            )
            self.session.add(new_song)
            success_count += 1
            print(f"[{count}] 入库成功: {s['title']}")
            
            # 批量 commit
            if success_count % 20 == 0:
                self.session.commit()
            
            # 避免 API 速率限制
            time.sleep(0.2)
            
        self.session.commit()
        self.session.close()
        print(f"Step 3 完成: 新增入库 {success_count} 首歌曲。")

    def _api_fetch_lyric(self, song_id):
        url = f"http://music.163.com/api/song/lyric?id={song_id}&lv=1&kv=1&tv=-1"
        headers = {
            "Referer": "http://music.163.com",
            # "User-Agent": "Mozilla/5.0 ..." 
        }
        try:
            resp = requests.get(url, headers=headers, timeout=5)
            data = resp.json()
            if "lrc" in data and "lyric" in data["lrc"]:
                return data["lrc"]["lyric"]
        except:
            pass
        return ""

    def _clean_lyrics(self, raw_lyric):
        if not raw_lyric:
            return ""
        # 去时间轴
        lyric = re.sub(r"\[\d{2}:\d{2}\.\d{2,3}\]", "", raw_lyric)
        # 去元数据
        lyric = re.sub(r"^.*(作词|作曲|编曲|制作|发行|混音|母带).*$", "", lyric, flags=re.MULTILINE)
        lines = [line.strip() for line in lyric.split("\n") if line.strip()] 
        return "\n".join(lines)

if __name__ == "__main__":
    crawler = NetCloudCrawler()
    
    # 手动控制执行步骤，或者一次性跑完
    # 建议第一次先跑 step 1，确认无误再 step 2...
    
    # 交互式选择 或者 顺序执行
    print("请选择要执行的步骤:")
    print("1: 爬取歌单 (to playlists.csv)")
    print("2: 爬取歌曲列表 (to songs_meta.csv)")
    print("3: 爬取歌词并入库 (to DB)")
    print("all: 按顺序执行所有步骤")
    
    import sys
    if len(sys.argv) > 1:
        choice = sys.argv[1]
    else:
        # 为了演示方便，这里默认顺序执行所有，或者让用户之后再改
        # 鉴于 Agent 模式，最好一次性写好自动执行脚本
        choice = "all" 

    if choice == "1":
        crawler.step1_fetch_playlists()
    elif choice == "2":
        crawler.step2_fetch_songs_IDs()
    elif choice == "3":
        crawler.step3_fetch_lyrics_and_save()
    elif choice == "all":
        crawler.step1_fetch_playlists()
        crawler.step2_fetch_songs_IDs()
        crawler.step3_fetch_lyrics_and_save()
    else:
        print("Invalid choice")
