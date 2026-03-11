"""
专辑封面补录脚本

对数据库中 album_cover IS NULL 的歌曲，
批量调用网易云 song/detail API 补录封面 URL。

用法：
    python backfill_album_covers.py

环境变量（与 db_init.py 一致）：
    DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME
"""

import os
import time
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ── 数据库配置 ────────────────────────────────────────
DB_URL = "postgresql://{user}:{password}@{host}:{port}/{db}".format(
    user=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "postgres"),
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=os.getenv("DB_PORT", "5433"),
    db=os.getenv("DB_NAME", "music_db"),
)

# ── 网易云 API ────────────────────────────────────────
NETEASE_DETAIL_API = "http://music.163.com/api/song/detail"
HEADERS = {
    "Referer": "https://music.163.com/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

BATCH_SIZE = 50       # 每次请求的歌曲数量（网易云单次上限）
SLEEP_BETWEEN = 1.0   # 批次间等待秒数，避免被限流
MAX_RETRIES = 3       # 单批次请求失败重试次数


def fetch_covers(song_ids: list[str]) -> dict[str, str]:
    """
    批量请求网易云 song/detail，返回 {song_id: picUrl} 字典。
    找不到封面的歌曲不会出现在结果里。
    """
    ids_param = str([int(i) for i in song_ids])  # "[123, 456, ...]"
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(
                NETEASE_DETAIL_API,
                params={"ids": ids_param},
                headers=HEADERS,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            result = {}
            for song in data.get("songs", []):
                sid = str(song.get("id", ""))
                pic_url = song.get("album", {}).get("picUrl", "")
                if sid and pic_url:
                    result[sid] = pic_url
            return result
        except Exception as e:
            print(f"    [重试 {attempt+1}/{MAX_RETRIES}] 请求失败: {e}")
            time.sleep(2 ** attempt)
    return {}


def main():
    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 查询所有缺封面的歌曲 ID
    rows = session.execute(
        text("SELECT id FROM songs WHERE album_cover IS NULL ORDER BY id")
    ).fetchall()
    total = len(rows)
    print(f"共 {total} 首歌曲缺少封面，开始补录...\n")

    if total == 0:
        print("无需补录，退出。")
        session.close()
        return

    updated = 0
    failed_batches = 0

    for batch_start in range(0, total, BATCH_SIZE):
        batch_ids = [r[0] for r in rows[batch_start: batch_start + BATCH_SIZE]]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE
        print(f"[{batch_num}/{total_batches}] 处理 {len(batch_ids)} 首...")

        covers = fetch_covers(batch_ids)

        if not covers:
            print(f"    ! 本批次未获取到任何封面，跳过")
            failed_batches += 1
        else:
            # 批量 UPDATE
            for sid, pic_url in covers.items():
                session.execute(
                    text("UPDATE songs SET album_cover = :url WHERE id = :id"),
                    {"url": pic_url, "id": sid},
                )
            session.commit()
            updated += len(covers)
            print(f"    ✓ 本批次补录 {len(covers)}/{len(batch_ids)} 首")

        time.sleep(SLEEP_BETWEEN)

    session.close()

    print(f"\n========== 补录完成 ==========")
    print(f"成功补录: {updated} / {total} 首")
    if failed_batches:
        print(f"失败批次: {failed_batches}，可重新运行脚本补录剩余部分")


if __name__ == "__main__":
    main()
