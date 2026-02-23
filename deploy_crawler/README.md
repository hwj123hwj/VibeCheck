# VibeCheck 闊充箰鏁版嵁鐖櫕閮ㄧ讲鎸囧崡

鏈枃浠跺す鍖呭惈浜嗗湪鏈嶅姟鍣ㄤ笂閮ㄧ讲 VibeCheck 鐖櫕鎵€闇€鐨勬墍鏈夋枃浠躲€?
## 鍖呭惈鍐呭

*   `app.py`: 鐖櫕涓荤▼搴?(绾?Python, 鏃犻渶娴忚鍣?銆?*   `db_init.py`: 鏁版嵁搴撳垵濮嬪寲鑴氭湰銆?*   `Dockerfile`: 鐖櫕瀹瑰櫒鏋勫缓鏂囦欢銆?*   `docker-compose.yml`: 涓€閿惎鍔ㄦ暟鎹簱鍜岀埇铏湇鍔°€?*   `requirements.txt`: Python 渚濊禆銆?
## 閮ㄧ讲姝ラ

1.  **涓婁紶鏂囦欢**
    灏?`deploy_crawler` 鏁翠釜鏂囦欢澶逛笂浼犲埌鎮ㄧ殑 Linux 鏈嶅姟鍣ㄣ€?
2.  **杩涘叆鐩綍**
    ```bash
    cd deploy_crawler
    ```

3.  **鍚姩鏈嶅姟**
    浣跨敤 Docker Compose 涓€閿瀯寤哄苟鍚姩锛?    ```bash
    docker-compose up --build -d
    ```
    *   `-d` 琛ㄧず鍦ㄥ悗鍙拌繍琛屻€?
4.  **鏌ョ湅鏃ュ織**
    鏌ョ湅鐖櫕杩愯杩涘害鍜屾棩蹇楋細
    ```bash
    docker-compose logs -f crawler
    ```
    
    鏌ョ湅鏁版嵁搴撴棩蹇楋細
    ```bash
    docker-compose logs -f db
    ```

5.  **鍋滄鏈嶅姟**
    ```bash
    docker-compose down
    ```

## 鏁版嵁搴撲俊鎭?
*   **Host**: `localhost` (鏈嶅姟鍣ㄥ唴閮ㄤ簰鑱斾娇鐢?`db`)
*   **Port**: `5433` (鏆撮湶缁欏閮ㄧ殑绔彛锛屽唴閮ㄤ娇鐢?5432)
*   **User**: `root`
*   **Password**: `<set-in-.env>`
*   **Database**: `music_db`

鏁版嵁灏嗘寔涔呭寲淇濆瓨鍦?Docker Volume `db_data` 涓€?
