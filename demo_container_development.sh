#!/bin/bash

# APISIX 插件和 Redis 容器化开发演示

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║     APISIX 插件和 Redis 容器化开发演示                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 函数: 打印步骤
print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

# 函数: 打印成功
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# 函数: 打印信息
print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

# 检查容器是否运行
check_containers() {
    print_step "检查容器运行状态..."
    
    if ! docker-compose ps | grep -q "cdn-apisix"; then
        echo -e "${RED}✗ APISIX 容器未运行${NC}"
        echo "请先运行: docker-compose up -d"
        exit 1
    fi
    print_success "APISIX 容器运行中"
    
    if ! docker-compose ps | grep -q "cdn-redis"; then
        echo -e "${RED}✗ Redis 容器未运行${NC}"
        echo "请先运行: docker-compose up -d"
        exit 1
    fi
    print_success "Redis 容器运行中"
}

# 演示 1: 在容器中查看 APISIX 插件
demo_apisix_plugins() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  演示 1: 查看 APISIX 插件                                   ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    print_step "列出容器中的所有插件..."
    docker-compose exec apisix ls -la /opt/apisix/plugins/ | tail -20
    
    print_success "插件列表已显示"
    echo ""
    
    print_step "查看 cdn_defense 插件内容 (前 30 行)..."
    docker-compose exec apisix head -30 /opt/apisix/plugins/cdn_defense.lua
    
    print_success "插件代码已显示"
}

# 演示 2: 创建并加载新插件
demo_create_plugin() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  演示 2: 创建新的 APISIX 插件                              ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    PLUGIN_NAME="demo_plugin"
    PLUGIN_FILE="apisix-plugins/${PLUGIN_NAME}.lua"
    
    print_step "创建演示插件 ${PLUGIN_NAME}.lua..."
    
    cat > "$PLUGIN_FILE" << 'EOF'
-- 演示插件
local core = require "apisix.core"
local ngx = ngx

local plugin_name = "demo_plugin"

local _M = {
    version = "1.0.0",
    priority = 1000,
    type = "http",
    name = plugin_name,
    schema = {
        type = "object",
        properties = {
            demo_header = {
                type = "string",
                default = "X-Demo-Plugin"
            }
        }
    }
}

function _M.access(conf, ctx)
    core.log.info("演示插件已加载!")
    ngx.header[conf.demo_header] = "demo_value"
end

return _M
EOF
    
    print_success "插件文件已创建: $PLUGIN_FILE"
    cat "$PLUGIN_FILE"
    echo ""
    
    print_step "重启 APISIX 加载新插件..."
    docker-compose restart apisix
    sleep 5
    
    print_step "验证插件已加载..."
    if docker-compose exec apisix curl -s http://localhost:9180/apisix/admin/plugins/list | grep -q "demo_plugin"; then
        print_success "演示插件已成功加载!"
    else
        print_info "插件可能需要更多时间加载，请稍后检查"
    fi
}

# 演示 3: Redis 基本操作
demo_redis_basic() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  演示 3: Redis 基本操作                                     ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    print_step "连接 Redis 并执行命令..."
    echo ""
    
    # 设置和获取值
    print_info "1. 设置键值对"
    docker-compose exec redis redis-cli -a redispass123 SET mykey "hello redis"
    echo ""
    
    print_info "2. 获取值"
    docker-compose exec redis redis-cli -a redispass123 GET mykey
    echo ""
    
    # 计数操作
    print_info "3. 计数操作"
    docker-compose exec redis redis-cli -a redispass123 INCR page_views
    docker-compose exec redis redis-cli -a redispass123 INCR page_views
    docker-compose exec redis redis-cli -a redispass123 GET page_views
    echo ""
    
    # 过期设置
    print_info "4. 设置过期时间"
    docker-compose exec redis redis-cli -a redispass123 SET temp_cache "temporary" EX 60
    echo "设置 temp_cache，60 秒后过期"
    docker-compose exec redis redis-cli -a redispass123 TTL temp_cache
    echo ""
    
    # 哈希操作
    print_info "5. 哈希操作 (存储对象)"
    docker-compose exec redis redis-cli -a redispass123 HSET user:1 name "Alice" age 30 city "Beijing"
    docker-compose exec redis redis-cli -a redispass123 HGETALL user:1
    echo ""
    
    # 列表操作
    print_info "6. 列表操作"
    docker-compose exec redis redis-cli -a redispass123 LPUSH tasks "task1" "task2" "task3"
    docker-compose exec redis redis-cli -a redispass123 LRANGE tasks 0 -1
    echo ""
    
    print_success "Redis 演示完成"
}

# 演示 4: 黑名单管理 (CDN 场景)
demo_redis_blacklist() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  演示 4: Redis 黑名单管理 (CDN 防御场景)                    ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    print_step "添加恶意 IP 到黑名单..."
    docker-compose exec redis redis-cli -a redispass123 SET "blacklist:192.168.1.100" "1"
    docker-compose exec redis redis-cli -a redispass123 SET "blacklist:10.0.0.50" "1"
    docker-compose exec redis redis-cli -a redispass123 EXPIRE "blacklist:192.168.1.100" 3600
    docker-compose exec redis redis-cli -a redispass123 EXPIRE "blacklist:10.0.0.50" 3600
    print_success "黑名单已添加"
    echo ""
    
    print_step "检查 IP 是否在黑名单..."
    echo -n "192.168.1.100 在黑名单中: "
    docker-compose exec redis redis-cli -a redispass123 GET "blacklist:192.168.1.100"
    
    echo -n "8.8.8.8 在黑名单中: "
    docker-compose exec redis redis-cli -a redispass123 GET "blacklist:8.8.8.8" || echo "(nil - 未在黑名单)"
    echo ""
    
    print_step "查看所有黑名单 IP..."
    docker-compose exec redis redis-cli -a redispass123 KEYS "blacklist:*"
    echo ""
    
    print_step "查看黑名单数量..."
    docker-compose exec redis redis-cli -a redispass123 DBSIZE
    echo ""
    
    print_success "黑名单演示完成"
}

# 演示 5: 请求统计
demo_redis_statistics() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  演示 5: Redis 请求统计                                    ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    print_step "模拟请求统计..."
    
    # 模拟来自不同 IP 的请求
    for i in {1..5}; do
        docker-compose exec redis redis-cli -a redispass123 INCR "requests:192.168.1.10"
    done
    
    for i in {1..3}; do
        docker-compose exec redis redis-cli -a redispass123 INCR "requests:192.168.1.20"
    done
    
    docker-compose exec redis redis-cli -a redispass123 INCR "requests:192.168.1.30"
    
    print_success "请求已记录"
    echo ""
    
    print_step "显示请求统计..."
    echo "192.168.1.10 的请求数: $(docker-compose exec redis redis-cli -a redispass123 GET 'requests:192.168.1.10')"
    echo "192.168.1.20 的请求数: $(docker-compose exec redis redis-cli -a redispass123 GET 'requests:192.168.1.20')"
    echo "192.168.1.30 的请求数: $(docker-compose exec redis redis-cli -a redispass123 GET 'requests:192.168.1.30')"
    echo ""
    
    print_step "清理统计数据..."
    docker-compose exec redis redis-cli -a redispass123 FLUSHDB
    print_success "数据已清理"
}

# 演示 6: APISIX 与 Redis 的交互
demo_apisix_redis_interaction() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  演示 6: APISIX 与 Redis 交互                              ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    print_step "查看 APISIX 中的 Redis 连接..."
    print_info "APISIX 插件使用 lua-resty-redis 库连接 Redis"
    echo ""
    
    print_step "验证 APISIX 可以连接到 Redis..."
    if docker-compose exec apisix bash -c 'redis-cli -h redis -p 6379 -a redispass123 ping' &>/dev/null; then
        print_success "APISIX 可以成功连接到 Redis"
    else
        print_info "从 APISIX 容器连接 Redis..."
    fi
    echo ""
    
    print_info "在 APISIX 插件中使用 Redis 的示例:"
    echo ""
    cat << 'EOF'
local redis = require "resty.redis"
local red = redis:new()
red:connect("redis", 6379)
red:auth("redispass123")

-- 检查黑名单
local is_blocked = red:get("blacklist:" .. remote_ip)

-- 增加请求计数
red:incr("requests:" .. remote_ip)

-- 获取配置
red:hgetall("tenant:" .. tenant_id)

red:close()
EOF
}

# 主菜单
main_menu() {
    while true; do
        echo ""
        echo "╔════════════════════════════════════════════════════════════╗"
        echo "║           APISIX 和 Redis 容器化开发演示菜单             ║"
        echo "╚════════════════════════════════════════════════════════════╝"
        echo ""
        echo "1. 查看 APISIX 插件"
        echo "2. 创建并加载新插件"
        echo "3. Redis 基本操作演示"
        echo "4. Redis 黑名单管理演示"
        echo "5. Redis 请求统计演示"
        echo "6. APISIX 与 Redis 交互说明"
        echo "7. 全部演示"
        echo "0. 退出"
        echo ""
        read -p "请选择 (0-7): " choice
        
        case $choice in
            1) demo_apisix_plugins ;;
            2) demo_create_plugin ;;
            3) demo_redis_basic ;;
            4) demo_redis_blacklist ;;
            5) demo_redis_statistics ;;
            6) demo_apisix_redis_interaction ;;
            7)
                demo_apisix_plugins
                demo_create_plugin
                demo_redis_basic
                demo_redis_blacklist
                demo_redis_statistics
                demo_apisix_redis_interaction
                ;;
            0)
                echo "退出演示，再见！"
                exit 0
                ;;
            *)
                echo "无效选择，请重试"
                ;;
        esac
        
        read -p "按 Enter 继续..."
    done
}

# 主程序
cd "$(dirname "$0")"
check_containers
main_menu
