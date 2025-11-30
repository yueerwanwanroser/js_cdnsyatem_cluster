#!/bin/bash

# 容器化开发启动脚本 - 简化版本

set -e

cd "$(dirname "$0")"

echo "╔════════════════════════════════════════╗"
echo "║  Docker 容器化 CDN 防御系统            ║"
echo "╚════════════════════════════════════════╝"
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装"
    exit 1
fi

echo "✅ Docker 已检查"
echo ""
echo "🚀 启动容器化开发环境..."
echo ""

# 停止已存在的容器
echo "停止现有容器..."
docker-compose down 2>/dev/null || true

# 构建镜像
echo "构建镜像..."
docker-compose build --no-cache

# 启动服务
echo "启动所有服务..."
docker-compose up -d

echo ""
echo "⏳ 等待服务就绪..."
sleep 10

# 检查服务状态
echo ""
echo "📊 服务状态:"
docker-compose ps

echo ""
echo "✅ 所有服务已启动！"
echo ""
echo "╔════════════════════════════════════════╗"
echo "║         访问信息                       ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "🌐 后端服务:"
echo "   API:          http://localhost:8000"
echo "   文档:         http://localhost:8000/api/docs/"
echo "   Admin:        http://localhost:8000/admin/"
echo "   凭证:         admin / admin123"
echo ""
echo "🌐 前端服务:"
echo "   生产:         http://localhost"
echo "   开发:         http://localhost:5173"
echo ""
echo "🌐 基础设施:"
echo "   APISIX:       http://localhost:9180/apisix/admin"
echo "   etcd:         http://localhost:2379"
echo "   Redis:        localhost:6379"
echo "   PostgreSQL:   localhost:5432"
echo ""
echo "📊 监控:"
echo "   Prometheus:   http://localhost:9090"
echo "   Grafana:      http://localhost:3000 (admin/grafana123)"
echo ""
echo "📝 查看日志:"
echo "   docker-compose logs -f"
echo ""
echo "🛑 停止服务:"
echo "   docker-compose down"
echo ""
