# Redis 容器化使用指南

## 📌 概述

Redis 作为高性能缓存层完全运行在 Docker 容器中，支持：
- 缓存数据存储
- 黑名单管理
- 配置同步
- 实时数据统计
- Pub/Sub 消息通信

## 🐳 Redis 容器配置

### Docker Compose 中的 Redis

```yaml
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
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
```

## 🚀 快速开始

### 1. 启动 Redis 容器

```bash
# 启动所有容器（包括 Redis）
docker-compose up -d

# 验证 Redis 运行
docker-compose ps | grep redis

# 查看 Redis 日志
docker-compose logs redis
```

### 2. 连接到 Redis

#### 方式 1: 使用 redis-cli (推荐)

```bash
# 连接到 Redis (需要密码)
docker-compose exec redis redis-cli -a redispass123

# 或指定主机和端口
docker-compose exec redis redis-cli -h redis -p 6379 -a redispass123
```

#### 方式 2: 在本地机器上连接

```bash
# 如果本地安装了 redis-cli
redis-cli -h localhost -p 6379 -a redispass123

# 或使用 Docker 中的 redis-cli
docker run -it --rm redis:7-alpine redis-cli -h host.docker.internal -p 6379 -a redispass123
```

## 💾 Redis 数据结构和操作

### 基本命令

```bash
# 进入 Redis CLI
docker-compose exec redis redis-cli -a redispass123

# 连接后的常用命令

# 键管理
KEYS *                    # 列出所有键
EXISTS key_name           # 检查键是否存在
DEL key_name             # 删除键
EXPIRE key_name 3600     # 设置过期时间 (秒)
TTL key_name             # 查看剩余过期时间
TYPE key_name            # 查看键的数据类型
```

### 字符串操作

```redis
# 设置和获取
SET key value                    # 设置字符串值
GET key                          # 获取字符串值
SETNX key value                 # 仅当键不存在时设置
GETSET key new_value            # 获取旧值并设置新值

# 数值操作
INCR counter                    # 递增
DECR counter                    # 递减
INCRBY counter 10               # 增加指定数量
DECRBY counter 5                # 减少指定数量

# 字符串操作
APPEND key " more text"         # 追加字符
STRLEN key                      # 获取长度
GETRANGE key 0 5                # 获取子字符串
SETRANGE key 0 "new"            # 设置子字符串
```

### 哈希操作

```redis
# 基本操作
HSET hash field value           # 设置哈希字段
HGET hash field                 # 获取哈希字段
HMSET hash f1 v1 f2 v2         # 设置多个字段
HMGET hash f1 f2                # 获取多个字段
HGETALL hash                    # 获取所有字段和值
HKEYS hash                      # 获取所有字段
HVALS hash                      # 获取所有值
HLEN hash                       # 获取字段数量
HEXISTS hash field              # 检查字段是否存在
HDEL hash field                 # 删除字段
```

### 列表操作

```redis
# 添加元素
LPUSH list value                # 左端添加
RPUSH list value                # 右端添加
LPUSHX list value               # 仅当列表存在时左端添加

# 移除元素
LPOP list                       # 左端移除并返回
RPOP list                       # 右端移除并返回

# 查看列表
LLEN list                       # 获取列表长度
LRANGE list 0 -1                # 获取范围内元素
LINDEX list 0                   # 获取指定索引元素
```

### 集合操作

```redis
# 添加元素
SADD set member                 # 添加元素
SMEMBERS set                    # 获取所有元素
SCARD set                       # 获取集合大小
SISMEMBER set member            # 检查元素是否存在

# 集合运算
SUNION set1 set2                # 并集
SINTER set1 set2                # 交集
SDIFF set1 set2                 # 差集
```

### 有序集合操作

```redis
# 基本操作
ZADD zset 1 member             # 添加元素及分数
ZRANGE zset 0 -1               # 获取范围内元素
ZREVRANGE zset 0 -1            # 逆序获取
ZCARD zset                      # 获取元素数量
ZSCORE zset member             # 获取元素分数
ZREM zset member               # 删除元素

# 范围查询
ZRANGEBYSCORE zset 0 100       # 按分数范围查询
```

## 🛡️ CDN 防御系统中的 Redis 使用

### 黑名单管理

```bash
# 连接 Redis
docker-compose exec redis redis-cli -a redispass123

# 添加 IP 到黑名单
SET blacklist:192.168.1.100 1
SET blacklist:10.0.0.50 1

# 设置过期时间 (1 小时)
EXPIRE blacklist:192.168.1.100 3600

# 查看所有黑名单
KEYS blacklist:*

# 检查 IP 是否在黑名单
GET blacklist:192.168.1.100

# 移除黑名单
DEL blacklist:192.168.1.100
```

### 请求计数

```redis
# 记录 IP 请求次数
INCR requests:192.168.1.1

# 设置过期 (1 分钟内)
EXPIRE requests:192.168.1.1 60

# 获取请求次数
GET requests:192.168.1.1

# 查看所有计数
KEYS requests:*
```

### 缓存配置

```redis
# 缓存租户配置
HSET tenant:1 rate_limit 1000
HSET tenant:1 threat_threshold 75
HSET tenant:1 enabled_defense true

# 获取配置
HGETALL tenant:1

# 更新配置
HSET tenant:1 rate_limit 2000

# 缓存路由信息
SET route:api-1 '{"path":"/api","upstream":"localhost:8000"}'
EXPIRE route:api-1 3600

# 获取缓存
GET route:api-1
```

### 实时统计

```redis
# 记录访问统计
INCR stats:total_requests
INCR stats:blocked_requests
INCR stats:cache_hits

# 获取统计
GET stats:total_requests
GET stats:blocked_requests
GET stats:cache_hits

# 每小时清零
INCRBY stats:hourly:requests 1
EXPIRE stats:hourly:requests 3600
```

## 🔄 Django 与 Redis 的交互

### Django ORM 中使用 Redis

```bash
# 进入 Django 容器
docker-compose exec django bash

# 进入 Python shell
python manage.py shell

# 在 Python 中操作 Redis
from django.core.cache import cache

# 设置缓存
cache.set('key', 'value', 3600)

# 获取缓存
value = cache.get('key')

# 删除缓存
cache.delete('key')

# 清空所有缓存
cache.clear()

# 原生 Redis 操作
from django.core.cache import caches
redis_cache = caches['default']
redis_cache.client.get_client().incr('counter')
```

### Django 代码中的 Redis

```python
# views.py
from django.core.cache import cache
from django_redis import get_redis_connection

def my_view(request):
    # 使用 Django 缓存
    key = f"user:{request.user.id}:profile"
    profile = cache.get(key)
    
    if not profile:
        profile = get_user_profile(request.user.id)
        cache.set(key, profile, 3600)
    
    # 使用原生 Redis
    redis_conn = get_redis_connection("default")
    redis_conn.incr(f"page_views:{request.path}")
    
    return JsonResponse(profile)
```

## 📊 Redis 监控和维护

### 查看 Redis 统计

```bash
# 进入 Redis CLI
docker-compose exec redis redis-cli -a redispass123

# 获取服务器信息
INFO

# 获取内存使用
INFO memory

# 获取数据统计
INFO stats

# 获取客户端信息
CLIENT LIST

# 获取所有键数量
DBSIZE

# 获取键的分布 (指定匹配模式)
KEYS "*"
KEYS "blacklist:*"
KEYS "requests:*"
```

### 性能分析

```redis
# 监控命令执行
MONITOR

# 获取慢查询日志
SLOWLOG GET 10

# 获取最慢的查询
SLOWLOG GET

# 重置慢查询日志
SLOWLOG RESET

# 获取实时统计
INFO stats
```

### 备份和恢复

```bash
# 备份 Redis 数据
docker-compose exec redis redis-cli -a redispass123 --rdb /tmp/dump.rdb

# 或使用 volume 备份
docker run --rm -v cdn-defense-system_redis_data:/data -v $(pwd):/backup \
  redis:7-alpine tar czf /backup/redis_backup.tar.gz -C /data .

# 恢复数据
docker run --rm -v cdn-defense-system_redis_data:/data -v $(pwd):/backup \
  redis:7-alpine tar xzf /backup/redis_backup.tar.gz -C /data
```

## 🔌 在 APISIX 插件中使用 Redis

### Lua 中使用 Redis

```lua
-- apisix-plugins/cdn_defense.lua
local redis = require "resty.redis"
local core = require "apisix.core"

function _M.access(conf, ctx)
    local red = redis:new()
    
    -- 连接 Redis (容器内通过 redis 主机名)
    local ok, err = red:connect("redis", 6379)
    if not ok then
        core.log.error("Redis 连接失败: ", err)
        return
    end
    
    -- 认证
    ok, err = red:auth("redispass123")
    if not ok then
        core.log.error("Redis 认证失败: ", err)
        red:close()
        return
    end
    
    local remote_ip = ngx.var.remote_addr
    
    -- 检查黑名单
    local is_blacklisted, err = red:get("blacklist:" .. remote_ip)
    if err then
        core.log.error("获取黑名单失败: ", err)
    end
    
    if is_blacklisted then
        red:close()
        return 403, { message = "IP 在黑名单中" }
    end
    
    -- 增加请求计数
    local req_count, err = red:incr("requests:" .. remote_ip)
    red:expire("requests:" .. remote_ip, 60)
    
    if req_count > conf.rate_limit then
        red:close()
        return 429, { message = "请求过于频繁" }
    end
    
    -- 更新统计
    red:incr("stats:total_requests")
    
    red:close()
end
```

## 🚨 常见问题排除

### Redis 无法连接

```bash
# 检查容器是否运行
docker-compose ps redis

# 查看 Redis 日志
docker-compose logs redis

# 测试连接
docker-compose exec redis redis-cli ping

# 测试密码
docker-compose exec redis redis-cli -a redispass123 ping
```

### 内存使用过高

```bash
# 查看内存使用
docker-compose exec redis redis-cli -a redispass123 INFO memory

# 查看键大小分布
docker-compose exec redis redis-cli -a redispass123 --bigkeys

# 清理过期键
docker-compose exec redis redis-cli -a redispass123 FLUSHDB
```

### 性能缓慢

```bash
# 查看慢查询
docker-compose exec redis redis-cli -a redispass123 SLOWLOG GET 10

# 监控实时命令
docker-compose exec redis redis-cli -a redispass123 MONITOR

# 优化配置 (编辑 docker-compose.yml)
command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru
```

## 🔧 常用命令速查表

### 启动和连接

```bash
# 启动所有容器
docker-compose up -d

# 连接 Redis
docker-compose exec redis redis-cli -a redispass123

# 查看日志
docker-compose logs -f redis
```

### 数据操作

| 场景 | 命令 |
|-----|------|
| 设置缓存 | SET key value EX 3600 |
| 获取缓存 | GET key |
| 删除缓存 | DEL key |
| 查看所有键 | KEYS * |
| 添加黑名单 | SET blacklist:ip 1 |
| 检查黑名单 | GET blacklist:ip |
| 增加计数 | INCR counter |
| 查看计数 | GET counter |

### 维护操作

```bash
# 查看内存使用
INFO memory

# 查看所有键
KEYS *

# 清空数据库
FLUSHDB

# 获取统计信息
INFO stats

# 监控命令
MONITOR
```

## 📈 性能优化建议

### 1. 设置合理的 Redis 内存限制

```yaml
# docker-compose.yml
redis:
  command: redis-server --appendonly yes --requirepass redispass123 --maxmemory 2gb --maxmemory-policy allkeys-lru
```

### 2. 设置 TTL 避免内存溢出

```lua
-- 在插件中设置过期时间
redis:setex("key", 3600, "value")
redis:expire("key", 3600)
```

### 3. 使用连接池

```lua
-- 连接复用
local red = redis:new()
red:set_timeouts(1000, 1000, 1000)
red:connect("redis", 6379)
-- 使用 keepalive
red:set_keepalive(10000, 100)
```

## 📚 相关资源

- [Redis 官方文档](https://redis.io/documentation)
- [Redis Lua 脚本](https://redis.io/commands/eval)
- [lua-resty-redis](https://github.com/openresty/lua-resty-redis)
- [Django Redis](https://github.com/jazzband/django-redis)

## 总结

✅ **Redis - 完全容器化**
- 镜像: redis:7-alpine
- 容器名: cdn-redis
- 端口: 6379
- 密码: redispass123
- 数据卷: redis_data (持久化)

✅ **连接方式**
- 容器内: `docker-compose exec redis redis-cli`
- Django 中: 通过 REDIS_URL 环境变量
- APISIX 插件: 通过 lua-resty-redis 库
- 本地: `redis-cli -h localhost -p 6379`

✅ **常见用途**
- 缓存数据存储
- 黑名单管理
- 请求计数和限流
- 配置缓存
- 实时统计
- Pub/Sub 消息

所有 Redis 操作都在 Docker 容器中进行，确保数据持久化和高可用！
