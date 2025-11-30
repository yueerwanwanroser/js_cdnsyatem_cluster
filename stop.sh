#!/bin/bash

# CDN 防御系统停止脚本

set -e

echo "================================"
echo "停止 CDN 防御系统"
echo "================================"

# 进入项目目录
cd "$(dirname "$0")"

# 停止容器
echo "停止 Docker 容器..."
docker-compose -f docker/docker-compose.yml down

echo ""
echo "停止完成！"
echo ""
echo "数据保留在 volumes 中，下次启动时会恢复。"
echo ""
echo "如需清除所有数据，运行:"
echo "  docker-compose -f docker/docker-compose.yml down -v"
