#!/bin/bash

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印标题
print_title() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  CDN 防御系统 - 完整容器化部署                   ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"
}

# 打印子标题
print_section() {
    echo -e "\n${YELLOW}▶ $1${NC}"
}

# 检查依赖
check_dependencies() {
    print_section "检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}✗ Docker 未安装${NC}"
        echo "请访问: https://docs.docker.com/get-docker/"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker 已安装${NC}"
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}✗ Docker Compose 未安装${NC}"
        echo "请访问: https://docs.docker.com/compose/install/"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker Compose 已安装${NC}"
}

# 启停服务
manage_services() {
    local action=$1
    
    case $action in
        start)
            print_section "启动所有服务..."
            docker-compose up -d
            print_section "等待服务健康检查..."
            sleep 10
            ;;
        stop)
            print_section "停止所有服务..."
            docker-compose down
            ;;
        restart)
            print_section "重启所有服务..."
            docker-compose restart
            ;;
        logs)
            print_section "显示日志..."
            docker-compose logs -f
            ;;
        *)
            echo "未知命令: $action"
            exit 1
            ;;
    esac
}

# 显示服务状态
show_status() {
    print_section "服务状态"
    docker-compose ps
}

# 显示访问信息
show_access() {
    print_section "访问信息"
    echo ""
    echo -e "${GREEN}┌─ 后端服务${NC}"
    echo -e "  API 端点:     ${BLUE}http://localhost:8000${NC}"
    echo -e "  API 文档:     ${BLUE}http://localhost:8000/api/docs/${NC}"
    echo -e "  Admin:        ${BLUE}http://localhost:8000/admin/${NC}"
    echo -e "  用户名/密码:  ${YELLOW}admin / admin123${NC}"
    echo ""
    echo -e "${GREEN}┌─ 前端服务${NC}"
    echo -e "  生产环境:     ${BLUE}http://localhost${NC}"
    echo -e "  开发环境:     ${BLUE}http://localhost:5173${NC}"
    echo ""
    echo -e "${GREEN}┌─ 网关和基础设施${NC}"
    echo -e "  APISIX:       ${BLUE}http://localhost:9180/apisix/admin${NC}"
    echo -e "  etcd:         ${BLUE}http://localhost:2379${NC}"
    echo -e "  Redis:        ${BLUE}localhost:6379${NC}"
    echo -e "  PostgreSQL:   ${BLUE}localhost:5432${NC}"
    echo ""
    echo -e "${GREEN}┌─ 监控${NC}"
    echo -e "  Prometheus:   ${BLUE}http://localhost:9090${NC}"
    echo -e "  Grafana:      ${BLUE}http://localhost:3000${NC}"
    echo -e "  用户名/密码:  ${YELLOW}admin / grafana123${NC}"
    echo ""
}

# 显示帮助
show_help() {
    echo -e "${BLUE}用法:${NC} $0 [命令]"
    echo ""
    echo -e "${YELLOW}命令:${NC}"
    echo "  start          启动所有容器"
    echo "  stop           停止所有容器"
    echo "  restart        重启所有容器"
    echo "  logs           显示日志 (实时)"
    echo "  status         显示服务状态"
    echo "  access         显示访问信息"
    echo "  build          构建镜像"
    echo "  shell [svc]    进入服务的 Shell (例: $0 shell django)"
    echo "  db-shell       进入 PostgreSQL Shell"
    echo "  redis-cli      进入 Redis CLI"
    echo "  etcdctl        进入 etcd CLI"
    echo "  clean          清理容器和卷"
    echo "  help           显示帮助信息"
    echo ""
    echo -e "${YELLOW}示例:${NC}"
    echo "  $0 start           # 启动所有服务"
    echo "  $0 logs            # 查看日志"
    echo "  $0 shell django    # 进入 Django 容器"
    echo "  $0 db-shell        # 连接到 PostgreSQL"
}

# 进入容器 Shell
enter_shell() {
    local service=$1
    if [ -z "$service" ]; then
        echo "请指定服务名称 (django, frontend, postgres, redis, etcd, apisix)"
        exit 1
    fi
    
    case $service in
        django)
            docker-compose exec django bash
            ;;
        frontend)
            docker-compose exec frontend sh
            ;;
        postgres)
            docker-compose exec postgres psql -U cdnuser -d cdn_defense
            ;;
        redis)
            docker-compose exec redis redis-cli
            ;;
        etcd)
            docker-compose exec etcd /bin/sh
            ;;
        apisix)
            docker-compose exec apisix sh
            ;;
        *)
            echo "未知服务: $service"
            exit 1
            ;;
    esac
}

# PostgreSQL Shell
db_shell() {
    docker-compose exec postgres psql -U cdnuser -d cdn_defense
}

# Redis CLI
redis_cli() {
    docker-compose exec redis redis-cli -a redispass123
}

# etctcl 工具
etcdctl_tool() {
    docker-compose exec etcd etcdctl --endpoints=http://localhost:2379
}

# 清理
clean_up() {
    print_section "清理容器、卷和网络..."
    docker-compose down -v
    echo -e "${GREEN}✓ 清理完成${NC}"
}

# 构建镜像
build_images() {
    print_section "构建镜像..."
    docker-compose build --no-cache
    echo -e "${GREEN}✓ 构建完成${NC}"
}

# 主函数
main() {
    cd "$(dirname "$0")/.."
    
    print_title
    
    case ${1:-help} in
        start)
            check_dependencies
            manage_services start
            show_status
            show_access
            ;;
        stop)
            manage_services stop
            ;;
        restart)
            manage_services restart
            show_status
            ;;
        logs)
            manage_services logs
            ;;
        status)
            show_status
            show_access
            ;;
        access)
            show_access
            ;;
        build)
            build_images
            ;;
        shell)
            enter_shell $2
            ;;
        db-shell)
            db_shell
            ;;
        redis-cli)
            redis_cli
            ;;
        etcdctl)
            etcdctl_tool
            ;;
        clean)
            clean_up
            ;;
        help)
            show_help
            ;;
        *)
            echo -e "${RED}未知命令: $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
