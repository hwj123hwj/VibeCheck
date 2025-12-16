# VibeCheck 音乐数据爬虫部署指南

本文件夹包含了在服务器上部署 VibeCheck 爬虫所需的所有文件。

## 包含内容

*   `app.py`: 爬虫主程序 (纯 Python, 无需浏览器)。
*   `db_init.py`: 数据库初始化脚本。
*   `Dockerfile`: 爬虫容器构建文件。
*   `docker-compose.yml`: 一键启动数据库和爬虫服务。
*   `requirements.txt`: Python 依赖。

## 部署步骤

1.  **上传文件**
    将 `deploy_crawler` 整个文件夹上传到您的 Linux 服务器。

2.  **进入目录**
    ```bash
    cd deploy_crawler
    ```

3.  **启动服务**
    使用 Docker Compose 一键构建并启动：
    ```bash
    docker-compose up --build -d
    ```
    *   `-d` 表示在后台运行。

4.  **查看日志**
    查看爬虫运行进度和日志：
    ```bash
    docker-compose logs -f crawler
    ```
    
    查看数据库日志：
    ```bash
    docker-compose logs -f db
    ```

5.  **停止服务**
    ```bash
    docker-compose down
    ```

## 数据库信息

*   **Host**: `localhost` (服务器内部互联使用 `db`)
*   **Port**: `5433` (暴露给外部的端口，内部使用 5432)
*   **User**: `root`
*   **Password**: `15671040800q`
*   **Database**: `music_db`

数据将持久化保存在 Docker Volume `db_data` 中。
