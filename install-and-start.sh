#!/bin/bash

# ═══════════════════════════════════════════════════════════════════════════
# CDN 防御系统 - 完整安装和启动脚本
# 支持：自动安装 Docker、Docker Compose，然后启动系统
# ═══════════════════════════════════════════════════════════════════════════

set -e

cd "$(dirname "$0")"

echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                       ║"
echo "║     CDN 防御系统 - 一键安装与启动脚本                                 ║"
echo "║                                                                       ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 第 1 步：检查并安装 Docker
# ═══════════════════════════════════════════════════════════════════════════

echo "📦 第 1 步：检查 Docker..."
echo ""

if ! command -v docker &> /dev/null; then
    echo "⚠️  Docker 未检测到，正在安装..."
    echo ""
    
    # 更新包列表
    echo "📥 更新包列表..."
    apt-get update -qq
    
    # 安装依赖
    echo "📥 安装依赖..."
    apt-get install -y -qq \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        apt-transport-https
    
    # 添加 Docker 官方 GPG key
    echo "🔑 添加 Docker GPG key..."
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
        gpg --dearmor -o /etc/apt/keyrings/docker-archive-keyring.gpg 2>/dev/null || \
        curl -fsSL https://download.docker.com/linux/debian/gpg | \
        gpg --dearmor -o /etc/apt/keyrings/docker-archive-keyring.gpg
    
    # 添加 Docker 仓库
    echo "📦 添加 Docker 仓库..."
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker-archive-keyring.gpg] \
        https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null || \
        echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker-archive-keyring.gpg] \
        https://download.docker.com/linux/debian $(lsb_release -cs) stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # 更新包列表
    echo "📥 更新包列表..."
    apt-get update -qq
    
    # 安装 Docker
    echo "📥 安装 Docker..."
    apt-get install -y -qq \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-buildx-plugin \
        docker-compose-plugin
    
    echo "✅ Docker 安装完成"
else
    echo "✅ Docker 已安装: $(docker --version)"
fi

echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 第 2 步：检查并安装 Docker Compose
# ═══════════════════════════════════════════════════════════════════════════

echo "📦 第 2 步：检查 Docker Compose..."
echo ""

if ! command -v docker-compose &> /dev/null; then
    echo "ℹ️  使用 docker compose v2 (通过 Docker 插件)"
else
    echo "✅ Docker Compose 已安装: $(docker-compose --version)"
fi

# 验证 docker compose v2
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose 不可用"
    exit 1
fi

echo "✅ Docker Compose 可用: $(docker compose version)"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 第 3 步：启动 Docker 服务
# ═══════════════════════════════════════════════════════════════════════════

echo "🚀 第 3 步：启动 Docker 服务..."
echo ""

# 启动 Docker daemon
if ! systemctl is-active --quiet docker; then
    echo "启动 Docker daemon..."
    systemctl start docker
    sleep 2
fi

echo "✅ Docker 已运行"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 第 4 步：检查 docker-compose.yml
# ═══════════════════════════════════════════════════════════════════════════

echo "📋 第 4 步：检查配置文件..."
echo ""

if [ ! -f "docker/docker-compose.yml" ]; then
    echo "❌ 错误: docker/docker-compose.yml 不存在"
    exit 1
fi

echo "✅ 配置文件已找到"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# 第 5 步：启动 CDN 系统
# ═══════════════════════════════════════════════════════════════════════════

echo "🚀 第 5 步：启动 CDN 防御系统..."
echo ""

cd docker

# 停止现有容器
echo "⏹️  停止现有容器..."
docker compose down 2>/dev/null || true
echo ""

# 构建镜像
echo "🔨 构建镜像（首次启动可能需要 5-10 分钟）..."
echo ""
docker compose build --no-cache

echo ""
echo "⏳ 启动所有服务..."
docker compose up -d

echo ""
echo "⏳ 等待服务就绪（30 秒）..."
sleep 30

# 检查服务状态
echo ""
echo "📊 服务状态:"
docker compose ps

cd ..

echo ""
echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                       ║"
echo "║                    ✅ 启动完成！                                      ║"
echo "║                                                                       ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "🌐 访问地址："
echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   📱 前端："
echo "      • 主站:  http://localhost"
echo ""
echo "   🔧 后端 API："
echo "      • API:   http://localhost:8000"
echo "      • 文档:  http://localhost:8000/api/docs/"
echo "      • 管理:  http://localhost:8000/admin/"
echo "      • 账号:  admin / admin123"
echo ""
echo "   🛠️ 基础设施："
echo "      • APISIX 管理:  http://localhost:9180/apisix/admin"
echo "      • etcd:        http://localhost:2379"
echo "      • Redis:       localhost:6379"
echo "      • PostgreSQL:  localhost:5432"
echo ""
echo "   📊 监控："
echo "      • Prometheus:  http://localhost:9090"
echo "      • Grafana:     http://localhost:3000"
echo "      • 账号:        admin / grafana123"
echo ""
echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 常用命令："
echo "   • 查看日志:     docker compose -f docker/docker-compose.yml logs -f"
echo "   • 停止服务:     docker compose -f docker/docker-compose.yml down"
echo "   • 重启服务:     docker compose -f docker/docker-compose.yml restart"
echo "   • 查看统计:     docker stats"
echo ""
echo "💡 提示："
echo "   • 首次启动会拉取 Docker 镜像，可能需要 5-10 分钟"
echo "   • 如果遇到端口被占用，请修改 docker/docker-compose.yml"
echo "   • 所有数据保存在 Docker volumes 中，停止不会丢失数据"
echo ""
echo "🎉 祝您使用愉快！"
echo ""
