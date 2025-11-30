#!/bin/bash

################################################################################
#                                                                              #
#              CDN 防御系统 - 一站式部署脚本 (完整版)                          #
#                                                                              #
#  功能:                                                                       #
#    1. 自动安装 Docker                                                        #
#    2. 自动安装 Docker Compose                                                #
#    3. 构建 Django 应用镜像                                                    #
#    4. 启动所有必要的容器                                                      #
#    5. 验证部署状态                                                            #
#                                                                              #
################################################################################

set -e

# ═══════════════════════════════════════════════════════════════════════════
# 颜色定义
# ═══════════════════════════════════════════════════════════════════════════

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# 高亮提醒
ALERT_RED='\033[41;37m'
ALERT_GREEN='\033[42;37m'
ALERT_YELLOW='\033[43;30m'
ALERT_BLUE='\033[44;37m'

# ═══════════════════════════════════════════════════════════════════════════
# 函数定义
# ═══════════════════════════════════════════════════════════════════════════

print_header() {
    echo -e "\n${BLUE}╔═══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}${WHITE}$1${NC}${BLUE}║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════════╝${NC}\n"
}

print_step() {
    echo -e "\n${CYAN}▶ $1${NC}\n"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_alert() {
    echo -e "\n${ALERT_RED}┌─────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${ALERT_RED}│ ⚠️  重要提醒${NC}${ALERT_RED}                                                           │${NC}"
    echo -e "${ALERT_RED}├─────────────────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${ALERT_RED}│${NC} $1 ${ALERT_RED}│${NC}"
    echo -e "${ALERT_RED}└─────────────────────────────────────────────────────────────────────────┘${NC}\n"
}

print_info_box() {
    echo -e "\n${ALERT_BLUE}┌─────────────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${ALERT_BLUE}│${NC} ℹ️  $1 ${ALERT_BLUE}│${NC}"
    echo -e "${ALERT_BLUE}└─────────────────────────────────────────────────────────────────────────┘${NC}\n"
}

# ═══════════════════════════════════════════════════════════════════════════
# 开始部署
# ═══════════════════════════════════════════════════════════════════════════

clear

print_header "                  🚀 CDN 防御系统 - 一站式部署脚本"

cat << "EOF"

  ┌───────────────────────────────────────────────────────────────┐
  │                                                               │
  │  此脚本将完成以下操作:                                        │
  │                                                               │
  │  1️⃣  检查并安装 Docker                                        │
  │  2️⃣  检查并安装 Docker Compose                                │
  │  3️⃣  构建 Django 应用镜像 (493MB)                            │
  │  4️⃣  启动 PostgreSQL、Redis、etcd 等服务                     │
  │  5️⃣  启动 Django API 应用                                    │
  │  6️⃣  验证所有容器运行状态                                    │
  │                                                               │
  │  ⏱️  预计耗时: 10-30 分钟 (首次构建)                         │
  │  💾 所需磁盘空间: ~2GB                                       │
  │  📊 所需内存: ~2GB                                           │
  │                                                               │
  └───────────────────────────────────────────────────────────────┘

EOF

cd "$(dirname "$0")"

# ═══════════════════════════════════════════════════════════════════════════
# 第 1 步：检查 Docker
# ═══════════════════════════════════════════════════════════════════════════

print_header "第 1 步: Docker 检查与安装"

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    print_success "Docker 已安装: $DOCKER_VERSION"
else
    print_alert "未检测到 Docker，正在安装..."
    
    print_step "更新系统包列表..."
    apt-get update -qq || yum update -y > /dev/null 2>&1 || true
    
    print_step "安装 Docker..."
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    bash /tmp/get-docker.sh > /dev/null 2>&1
    
    print_success "Docker 已安装: $(docker --version)"
fi

# 启动 Docker daemon
print_step "确保 Docker daemon 运行..."
systemctl start docker 2>/dev/null || service docker start 2>/dev/null || true
sleep 2

# ═══════════════════════════════════════════════════════════════════════════
# 第 2 步：检查 Docker Compose
# ═══════════════════════════════════════════════════════════════════════════

print_header "第 2 步: Docker Compose 检查与安装"

if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version)
    print_success "Docker Compose 已安装: $COMPOSE_VERSION"
elif docker compose version &> /dev/null; then
    print_success "Docker Compose v2 已安装 (通过 Docker 插件)"
else
    print_alert "未检测到 Docker Compose，正在安装..."
    
    print_step "下载 Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose 2>/dev/null || \
        curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o ~/docker-compose 2>/dev/null
    
    if [ -f /usr/local/bin/docker-compose ]; then
        chmod +x /usr/local/bin/docker-compose
        print_success "Docker Compose 已安装: $(docker-compose --version)"
    elif [ -f ~/docker-compose ]; then
        chmod +x ~/docker-compose
        print_success "Docker Compose 已安装到 ~/docker-compose"
        export PATH="$PATH:$HOME"
    else
        print_error "Docker Compose 安装失败"
        exit 1
    fi
fi

# ═══════════════════════════════════════════════════════════════════════════
# 第 3 步：构建 Django 镜像
# ═══════════════════════════════════════════════════════════════════════════

print_header "第 3 步: 构建 Django 应用镜像"

if docker image inspect cdn-defense:django-latest &>/dev/null; then
    print_warning "Django 镜像已存在，跳过构建"
    print_info_box "如需重新构建，请运行: docker image rm cdn-defense:django-latest"
else
    print_alert "开始构建 Django 镜像 (这可能需要 5-15 分钟)..."
    
    print_step "阶段 1: 下载基础镜像和依赖..."
    docker build \
        -f docker/Dockerfile.django \
        -t cdn-defense:django-latest \
        -t cdn-defense:django-v1 \
        --progress=plain \
        . 2>&1 | tail -20
    
    IMAGE_SIZE=$(docker image inspect cdn-defense:django-latest --format='{{.Size}}' | awk '{printf "%.0f", $1/1024/1024}')
    print_success "Django 镜像构建完成！大小: ${IMAGE_SIZE}MB"
    print_info_box "镜像标签: cdn-defense:django-latest, cdn-defense:django-v1"
fi

# ═══════════════════════════════════════════════════════════════════════════
# 第 4 步：启动容器
# ═══════════════════════════════════════════════════════════════════════════

print_header "第 4 步: 启动容器"

print_step "准备 Docker Compose 配置..."

# 创建简化的 docker-compose 文件
cat > docker/docker-compose-deploy.yml << 'COMPOSE'
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
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U cdnuser -d cdn_defense"]
      interval: 10s
      timeout: 5s
      retries: 5

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
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/sync-status/"]
      interval: 30s
      timeout: 10s
      retries: 3

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

print_success "配置文件已生成"

print_step "停止现有容器..."
cd docker
if command -v docker-compose &> /dev/null; then
    docker-compose -f docker-compose-deploy.yml down 2>/dev/null || true
elif docker compose version &> /dev/null; then
    docker compose -f docker-compose-deploy.yml down 2>/dev/null || true
fi

print_alert "启动所有容器 (这可能需要 1-3 分钟)..."
if command -v docker-compose &> /dev/null; then
    docker-compose -f docker-compose-deploy.yml up -d
elif command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
    if [ -x ~/docker-compose ]; then
        ~/docker-compose -f docker-compose-deploy.yml up -d
    else
        docker compose -f docker-compose-deploy.yml up -d
    fi
fi

print_step "等待服务就绪 (30 秒)..."
sleep 30

cd ..

# ═══════════════════════════════════════════════════════════════════════════
# 第 5 步：验证部署
# ═══════════════════════════════════════════════════════════════════════════

print_header "第 5 步: 验证部署状态"

echo -e "\n${CYAN}容器运行状态:${NC}\n"
if command -v docker-compose &> /dev/null; then
    docker-compose -f docker/docker-compose-deploy.yml ps
else
    docker compose -f docker/docker-compose-deploy.yml ps
fi

print_step "检查容器日志..."
echo -e "\n${YELLOW}Django API 状态:${NC}"
docker logs cdn-django-api 2>&1 | tail -10 || print_warning "还在启动中..."

# ═══════════════════════════════════════════════════════════════════════════
# 部署完成
# ═══════════════════════════════════════════════════════════════════════════

print_header "                  ✅ 部署完成！"

cat << "EOF"

  ╔───────────────────────────────────────────────────────────────╗
  │                     🎉 系统已启动                             │
  ╚───────────────────────────────────────────────────────────────╝

EOF

print_info_box "🌐 立即访问以下地址:"

cat << "EOF"

  📱 前端 Web:
     • 地址: http://localhost
     • 说明: 主前端应用

  🔧 Django API:
     • 地址: http://localhost:8000
     • API 文档: http://localhost:8000/api/docs/
     • Admin 面板: http://localhost:8000/admin/
     • 登录凭证: admin / admin123

  📊 监控面板:
     • Grafana: http://localhost:3000
     • 登录凭证: admin / grafana123
     • Prometheus: http://localhost:9090

  💾 数据库:
     • PostgreSQL: localhost:5432
     • Redis: localhost:6379
     • etcd: localhost:2379

EOF

print_alert "重要: 首次访问请更改默认密码!"

cat << "EOF"

  📝 常用命令:

  # 查看容器状态
  docker ps -a

  # 查看日志
  docker logs -f cdn-django-api

  # 停止系统
  docker-compose -f docker/docker-compose-deploy.yml down

  # 重启服务
  docker-compose -f docker/docker-compose-deploy.yml restart

  # 清理资源
  docker system prune -a

  📖 文档位置:
  • 部署指南: DEPLOYMENT_SUMMARY.md
  • 项目说明: README.md
  • 快速开始: QUICKSTART.md

EOF

print_header "                 🚀 部署成功！现在可以使用系统了"

