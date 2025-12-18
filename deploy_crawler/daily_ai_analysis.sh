#!/bin/bash

# =================================================================
# VibeCheck 每日 AI 情感分析自动化脚本
# =================================================================

# 1. 获取脚本所在的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

LOG_FILE="$SCRIPT_DIR/ai_progress.log"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] >>> 自动任务启动: 准备执行 AI 情感分析..." >> "$LOG_FILE"

# 2. 检查 Docker 容器是否在运行，如果没开则启动
# up -d 会确保 db 和 crawler 都在线，但不会中断已有的连接
docker compose up -d >> "$LOG_FILE" 2>&1

# 3. 执行分析脚本
# 使用 -T 参数是因为 crontab 没有分配终端 (tty)
# 我们不使用 -d，让 shell 脚本保持打开直到分析任务完成 (2000/3000首结束)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 正在运行 batch_ai_analysis.py..." >> "$LOG_FILE"
docker compose exec -T crawler python /app/batch_ai_analysis.py >> "$LOG_FILE" 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] <<< 任务执行完毕 (或已达每日上限)。" >> "$LOG_FILE"
echo "------------------------------------------------------------------" >> "$LOG_FILE"
