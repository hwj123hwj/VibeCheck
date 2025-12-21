#!/bin/bash

# =================================================================
# VibeCheck 自动化部署脚本 (Docker 版)
# =================================================================

# 1. 进入部署目录
cd deploy_crawler

echo "🐋 正在启动/更新 Docker 容器..."
# --build 确保如果有 requirements.txt 的更新，镜像会重新构建
docker compose up -d --build

echo "🧹 清理过期的 Docker 镜像..."
docker image prune -f

# 2. 自动运行数据库迁移 (如果需要)
# 下面这些脚本运行多次是幂等的，所以每次部署跑一遍很安全
echo "🗄️ 检查并同步数据库表结构..."
docker compose exec -T crawler python /app/migrate_v3_updated_at.py
docker compose exec -T crawler python /app/migrate_v2_vibe_fields.py

echo "✅ 部署脚本执行完毕！"
