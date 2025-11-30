#!/bin/bash

# CDN 防御系统部署脚本

set -e

echo "================================"
echo "CDN 防御系统部署"
echo "================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ 需要安装 Docker${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ 需要安装 Docker Compose${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker 环境检查通过${NC}"

# 进入项目目录
cd "$(dirname "$0")"

# 创建必要的目录
echo "创建目录结构..."
mkdir -p docker/grafana-dashboards
mkdir -p monitoring
mkdir -p logs

echo -e "${GREEN}✓ 目录结构创建完成${NC}"

# 启动服务
echo ""
echo "启动 Docker 容器..."
docker-compose -f docker/docker-compose.yml up -d

echo ""
echo -e "${GREEN}✓ CDN 防御系统启动完成${NC}"

# 等待服务启动
echo ""
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo ""
echo "检查服务状态..."

# 检查 Redis
if curl -s http://localhost:6379 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis 已启动 (6379)${NC}"
else
    echo -e "${YELLOW}⚠ Redis 状态未知${NC}"
fi

# 检查 APISIX
if curl -s http://localhost:9180/apisix/admin/routes > /dev/null 2>&1; then
    echo -e "${GREEN}✓ APISIX 已启动 (9080)${NC}"
else
    echo -e "${YELLOW}⚠ APISIX 正在启动...${NC}"
fi

# 检查防御 API
if curl -s http://localhost:5000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 防御 API (节点1) 已启动 (5000)${NC}"
else
    echo -e "${YELLOW}⚠ 防御 API 正在启动...${NC}"
fi

# 检查防御 API 节点2
if curl -s http://localhost:5001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 防御 API (节点2) 已启动 (5001)${NC}"
else
    echo -e "${YELLOW}⚠ 防御 API 节点2 正在启动...${NC}"
fi

# 检查 Grafana
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Grafana 已启动 (3000)${NC}"
else
    echo -e "${YELLOW}⚠ Grafana 正在启动...${NC}"
fi

# 检查 Prometheus
if curl -s http://localhost:9090 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Prometheus 已启动 (9090)${NC}"
else
    echo -e "${YELLOW}⚠ Prometheus 正在启动...${NC}"
fi

echo ""
echo "================================"
echo "服务访问地址:"
echo "================================"
echo -e "${GREEN}APISIX 网关${NC}       : http://localhost:9080"
echo -e "${GREEN}APISIX 管理界面${NC}   : http://localhost:9180"
echo -e "${GREEN}防御 API (节点1)${NC}  : http://localhost:5000"
echo -e "${GREEN}防御 API (节点2)${NC}  : http://localhost:5001"
echo -e "${GREEN}Prometheus${NC}       : http://localhost:9090"
echo -e "${GREEN}Grafana${NC}          : http://localhost:3000 (admin/admin)"
echo ""
echo "================================"
echo "管理命令示例:"
echo "================================"
echo "# 列出所有租户"
echo "python admin_cli.py tenant list"
echo ""
echo "# 创建新租户"
echo "python admin_cli.py tenant create --id tenant-001"
echo ""
echo "# 添加 IP 到黑名单"
echo "python admin_cli.py blacklist add --tenant-id tenant-001 --ip 192.168.1.100"
echo ""
echo "# 查看统计信息"
echo "python admin_cli.py stats --tenant-id tenant-001"
echo ""
echo "# 查看日志"
echo "python admin_cli.py logs --tenant-id tenant-001"
echo ""
echo "================================"
echo "启动完成！"
echo "================================"
