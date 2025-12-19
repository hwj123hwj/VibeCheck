#!/bin/bash

# =================================================================
# VibeCheck 每日 AI 情感分析自动化脚本 (Crontab 稳健版)
# =================================================================

# 1. 强制注入系统路径，确保 crontab 环境能找到所有依赖命令
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# 2. 定位脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 3. 定义宿主机日志文件 (cron_ai.log)
LOG_FILE="$SCRIPT_DIR/cron_ai.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] >>> [HOST] 自动任务启动..." >> "$LOG_FILE"

# 4. 确保 Docker 容器处于运行状态
docker compose up -d >> "$LOG_FILE" 2>&1

# 5. 执行 Python 分析逻辑
# -T 标志用于非交互式 shell (crontab 环境必须)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] >>> [CONTAINER] 开始运行 batch_ai_analysis.py..." >> "$LOG_FILE"
docker compose exec -T crawler python /app/batch_ai_analysis.py >> "$LOG_FILE" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] <<< [HOST] 任务执行结束。" >> "$LOG_FILE"
echo "------------------------------------------------------------------" >> "$LOG_FILE"
