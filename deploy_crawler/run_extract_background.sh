#!/bin/bash

# 1. 确保在正确的目录
cd "$(dirname "$0")"

echo "🚀 [1/3] 正在同步最新的 Migration 字段..."
docker compose exec -T crawler python /app/migrate_v6_core_lyrics.py

echo "🚀 [2/4] 启动后台全量提取任务 (Top 10 版本)..."
# 使用 nohup 运行提取并等待完成（或者也可以后台叠加，但顺序执行更稳）
docker compose exec -T crawler python /app/batch_update_core_lyrics.py > extract.log 2>&1

echo "🚀 [3/4] 启动金句向量化任务 (Batch Vectorization)..."
nohup docker compose exec -T crawler python -u /app/batch_lyrics_vectorization.py >> extract.log 2>&1 &

# 获取后台向量化进程的 PID
echo $! > extract.pid

echo "✅ [4/4] 任务已送入后台！"
echo "------------------------------------------------"
echo "📊 查看进度，请运行: tail -f extract.log"
echo "🛑 停止任务，请运行: kill \$(cat extract.pid)"
echo "------------------------------------------------"
