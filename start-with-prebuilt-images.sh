#!/bin/bash

# ═══════════════════════════════════════════════════════════════════════════
# CDN 防御系统 - 使用预构建镜像启动脚本
# ═══════════════════════════════════════════════════════════════════════════

set -e

cd "$(dirname "$0")"

echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                       ║"
echo "║     CDN 防御系统 - 使用预构建镜像启动                                 ║"
echo "║                                                                       ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 检查镜像
# ═══════════════════════════════════════════════════════════════════════════

echo "📋 检查镜像..."
echo ""

if ! docker image inspect cdn-defense:django-latest &>/dev/null; then
    echo "❌ 错误: cdn-defense:django-latest 镜像不存在"
    echo "请先运行: bash build-images.sh"
    exit 1
fi

echo "✅ Django 镜像: cdn-defense:django-latest"

if docker image inspect cdn-defense:api-latest &>/dev/null; then
    echo "✅ API 镜像: cdn-defense:api-latest"
else
    echo "⚠️  API 镜像不存在，仅使用 Django 镜像"
fi

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 修改 docker-compose.yml
# ═══════════════════════════════════════════════════════════════════════════

echo "🔧 配置 Docker Compose..."
echo ""

# 备份原始文件
if [ ! -f "docker/docker-compose.yml.backup" ]; then
    cp docker/docker-compose.yml docker/docker-compose.yml.backup
    echo "✅ 已备份原始配置"
fi

# 更新镜像标签 (简单版本，仅使用关键服务)
cat > docker/docker-compose-production.yml << 'COMPOSE'
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: cdn-postgres
    environment:
      POSTGRES_USER: cdnuser
      POSTGRES_PASSWORD: cdnpass123
      POSTGRES_DB: cdn_defense
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - cdn-network

  redis:
    image: redis:7-alpine
    container_name: cdn-redis
    command: redis-server --appendonly yes --requirepass redispass123
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - cdn-network

  etcd:
    image: quay.io/coreos/etcd:v3.5.7
    container_name: cdn-etcd
    environment:
      ETCD_LISTEN_CLIENT_URLS: http://0.0.0.0:2379
      ETCD_ADVERTISE_CLIENT_URLS: http://etcd:2379
    ports:
      - "2379:2379"
    networks:
      - cdn-network

  django-api:
    image: cdn-defense:django-latest
    container_name: cdn-django-api
    environment:
      DATABASE_URL: postgresql://cdnuser:cdnpass123@postgres:5432/cdn_defense
      REDIS_URL: redis://:redispass123@redis:6379/0
      DEBUG: "False"
      ALLOWED_HOSTS: "*"
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
      - etcd
    networks:
      - cdn-network

  prometheus:
    image: prom/prometheus:latest
    container_name: cdn-prometheus
    volumes:
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - cdn-network

  grafana:
    image: grafana/grafana:latest
    container_name: cdn-grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: grafana123
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"
    networks:
      - cdn-network

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  cdn-network:
    driver: bridge
COMPOSE

echo "✅ 已生成 docker-compose-production.yml"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 启动服务
# ═══════════════════════════════════════════════════════════════════════════

echo "🚀 启动服务..."
echo ""

cd docker

# 停止现有容器
echo "⏹️  停止现有容器..."
~/docker-compose -f docker-compose-production.yml down 2>/dev/null || true

echo ""
echo "启动容器..."
~/docker-compose -f docker-compose-production.yml up -d

echo ""
echo "⏳ 等待服务就绪..."
sleep 15

# 检查状态
echo ""
echo "📊 服务状态:"
~/docker-compose -f docker-compose-production.yml ps

cd ..

echo ""
echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                       ║"
echo "║                    ✅ 启动完成！                                      ║"
echo "║                                                                       ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "�� 访问地址："
echo "   • Django API:  http://localhost:8000"
echo "   • Grafana:     http://localhost:3000 (admin/grafana123)"
echo "   • Prometheus:  http://localhost:9090"
echo ""

