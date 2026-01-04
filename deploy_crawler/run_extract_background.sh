#!/bin/bash

# 1. 确保在正确的目录
cd "$(dirname "$0")"

echo "🧹 [1/4] 清理旧进程防止死锁..."
docker compose exec -T crawler pkill -f batch_update_core_lyrics || true
docker compose exec -T crawler pkill -f batch_lyrics_vectorization || true

echo "🚀 [2/4] 开始提取精华歌词 (Top 10 版本)..."
echo "--- 任务启动于 $(date) ---" > extract.log
# 我们将整个后续过程放入一个后台子 shell 中
(
    # 第一步：同步执行提取
    docker compose exec -T crawler python -u /app/batch_update_core_lyrics.py >> extract.log 2>&1
    
    echo "🚀 [3/4] 提取完成，开始金句向量化..." >> extract.log
    # 第二步：紧接着执行向量化
    docker compose exec -T crawler python -u /app/batch_lyrics_vectorization.py >> extract.log 2>&1
    
    echo "✨ [4/4] 所有任务已于 $(date) 顺利结束！" >> extract.log
) &

# 记录整个后台任务链的 PID
echo $! > extract.pid

echo "✅ 任务流水线已送入后台执行！"
echo "------------------------------------------------"
echo "📊 实时监控进度: tail -f extract.log"
echo "🛑 强行终止任务: kill \$(cat extract.pid)"
echo "------------------------------------------------"
