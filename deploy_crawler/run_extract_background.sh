#!/bin/bash

# 1. 确保在正确的目录
cd "$(dirname "$0")"

echo "🚀 [1/3] 正在同步最新的 Migration 字段..."
docker compose exec -T crawler python /app/migrate_v6_core_lyrics.py

echo "🚀 [2/3] 启动后台全量提取任务 (Top 10 版本)..."
# 使用 nohup + exec 方式在后台运行，并将输出保存到 extract.log
nohup docker compose exec -T crawler python -u /app/batch_update_core_lyrics.py > extract.log 2>&1 &

# 获取最后一次后台任务的 PID (注意：这里拿到的是宿主机的 shell PID，实际是在容器内)
echo $! > extract.pid

echo "✅ [3/3] 任务已送入后台！"
echo "------------------------------------------------"
echo "📊 查看进度，请运行: tail -f extract.log"
echo "🛑 停止任务，请运行: kill \$(cat extract.pid)"
echo "------------------------------------------------"
