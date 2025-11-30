# APISIX 插件开发 - 容器化指南

## 概述

APISIX 插件完全运行在容器中，我们可以在容器环境中开发、测试和部署 Lua 插件。

## 🐳 APISIX 容器架构

```
┌─────────────────────────────────────┐
│   APISIX 容器 (apache/apisix:3.1)   │
│                                     │
│  ┌──────────────────────────────┐   │
│  │ 插件目录                      │   │
│  │ /opt/apisix/plugins/         │   │
│  │  ├── cdn_defense.lua         │   │
│  │  ├── rate_limit.lua          │   │
│  │  └── 其他插件...             │   │
│  └──────────────────────────────┘   │
│                                     │
│  ┌──────────────────────────────┐   │
│  │ 配置目录                      │   │
│  │ /usr/local/apisix/conf/      │   │
│  │  ├── config.yaml             │   │
│  │  ├── apisix.yaml             │   │
│  │  └── plugin_config.yaml      │   │
│  └──────────────────────────────┘   │
│                                     │
└─────────────────────────────────────┘
         ↓
    ┌────────────────────┐
    │ etcd (2379)       │
    │ 配置存储和管理     │
    └────────────────────┘
         ↓
    ┌────────────────────┐
    │ Redis (6379)      │
    │ 缓存层             │
    └────────────────────┘
```

## 📦 当前项目结构

```
apisix-plugins/
├── cdn_defense.lua          # CDN 防御插件
└── README.md

docker/
├── docker-compose.yml       # Docker Compose (APISIX 配置)
├── apisix_config.yaml      # APISIX 配置文件
└── entrypoint.sh           # 启动脚本
```

## 🚀 启动 APISIX 容器

### 查看 APISIX 容器状态

```bash
# 查看所有容器
docker-compose ps

# 查看 APISIX 日志
docker-compose logs apisix

# 查看 APISIX 容器详情
docker-compose ps apisix
```

### 进入 APISIX 容器

```bash
# 进入 APISIX 容器 Shell
docker-compose exec apisix bash

# 进入后可执行的命令
cd /opt/apisix
ls -la plugins/
cat conf/config.yaml
```

## 🔧 开发 APISIX 插件

### 方式 1: 直接编辑本地文件 (推荐)

APISIX 插件通过卷挂载同步到容器中。

#### 步骤 1: 在本地创建插件

```bash
# 编辑或创建新插件
nano apisix-plugins/my_defense.lua
```

#### 步骤 2: 编写 Lua 插件代码

```lua
-- apisix-plugins/my_defense.lua
local core = require "apisix.core"
local ngx = ngx

local plugin_name = "my_defense"

local _M = {
    version = "1.0.0",
    priority = 1000,
    type = "http",
    name = plugin_name,
    schema = {
        type = "object",
        properties = {
            enable_defense = {
                type = "boolean",
                default = true
            },
            threat_level = {
                type = "integer",
                minimum = 1,
                maximum = 100,
                default = 50
            }
        }
    }
}

function _M.access(conf, ctx)
    -- 在请求进入上游前执行
    
    if not conf.enable_defense then
        return
    end
    
    local remote_ip = ngx.var.remote_addr
    core.log.info("检查请求 IP: ", remote_ip, " 威胁等级: ", conf.threat_level)
    
    -- 执行防御逻辑
    if conf.threat_level > 75 then
        return 403, { message = "请求被拒绝" }
    end
end

function _M.body_filter(conf, ctx)
    -- 处理响应体
end

function _M.log(conf, ctx)
    -- 记录日志
    core.log.info("请求完成: ", ctx.var.uri)
end

return _M
```

#### 步骤 3: 重启 APISIX 容器

```bash
# APISIX 会自动检测插件文件变更
docker-compose restart apisix

# 或只重新加载配置
docker-compose exec apisix apisix ctl stop
docker-compose exec apisix apisix start
```

#### 步骤 4: 验证插件已加载

```bash
# 进入 APISIX 容器
docker-compose exec apisix bash

# 查看插件列表
curl http://localhost:9180/apisix/admin/plugins/list

# 或查看日志
docker-compose logs apisix | grep my_defense
```

### 方式 2: 在容器内编辑

```bash
# 进入 APISIX 容器
docker-compose exec apisix bash

# 编辑插件
vi /opt/apisix/plugins/my_defense.lua

# 保存后重启
exit
docker-compose restart apisix
```

## 📝 完整的 CDN 防御插件示例

### 现有插件位置

```bash
apisix-plugins/cdn_defense.lua
```

### 查看当前插件

```bash
# 查看 cdn_defense.lua
cat apisix-plugins/cdn_defense.lua

# 或在容器中查看
docker-compose exec apisix cat /opt/apisix/plugins/cdn_defense.lua
```

### 扩展现有插件

编辑 `apisix-plugins/cdn_defense.lua`，添加新功能：

```lua
-- 在 access 函数中添加新的防御逻辑
function _M.access(conf, ctx)
    -- 现有代码...
    
    -- 新增: 检查 User-Agent
    local user_agent = ngx.var.http_user_agent or ""
    if string.find(user_agent, "bot") then
        return 403, { message = "机器人请求被拒绝" }
    end
    
    -- 新增: 检查请求方法
    if conf.allowed_methods then
        local method = ngx.var.request_method
        if not conf.allowed_methods[method] then
            return 405, { message = "方法不允许" }
        end
    end
end
```

## 🧪 测试 APISIX 插件

### 方式 1: 通过 Admin API

#### 创建路由并应用插件

```bash
# 创建一个路由，应用 cdn_defense 插件
curl -X PUT http://localhost:9180/apisix/admin/routes/1 \
  -H 'Content-Type: application/json' \
  -d '{
    "uri": "/api/*",
    "upstream": {
      "type": "roundrobin",
      "nodes": {
        "localhost:8000": 1
      }
    },
    "plugins": {
      "cdn_defense": {
        "enable_defense": true,
        "threat_level": 75
      }
    }
  }'
```

#### 查看路由

```bash
curl http://localhost:9180/apisix/admin/routes/1
```

#### 测试路由

```bash
# 测试请求
curl http://localhost:9080/api/test

# 查看响应
# 如果威胁级别高，返回 403
```

### 方式 2: 容器内测试

```bash
# 进入 APISIX 容器
docker-compose exec apisix bash

# 测试插件加载
curl http://localhost:9180/apisix/admin/plugins/list | grep cdn_defense

# 测试 etcd 连接
etcdctl --endpoints=http://etcd:2379 get /apisix

# 测试路由
curl http://localhost:9080/api/test
```

## 🔌 APISIX 插件与 Redis 的交互

### 在插件中使用 Redis

#### 示例: 在 CDN 防御插件中使用 Redis 缓存黑名单

```lua
local redis = require "resty.redis"

function _M.access(conf, ctx)
    local red = redis:new()
    
    -- 连接 Redis (容器内通过 redis 主机名)
    local ok, err = red:connect("redis", 6379)
    if not ok then
        core.log.error("无法连接 Redis: ", err)
        return
    end
    
    -- 设置密码
    red:auth("redispass123")
    
    -- 获取远程 IP
    local remote_ip = ngx.var.remote_addr
    
    -- 检查 IP 是否在黑名单中
    local is_blacklisted = red:get("blacklist:" .. remote_ip)
    
    if is_blacklisted then
        red:close()
        return 403, { message = "IP 已被黑名单" }
    end
    
    -- 检查请求计数
    local request_count = red:incr("requests:" .. remote_ip)
    red:expire("requests:" .. remote_ip, 60)
    
    if request_count > conf.rate_limit then
        red:close()
        return 429, { message = "请求过于频繁" }
    end
    
    red:close()
end
```

### 在容器中操作 Redis

```bash
# 进入 Redis 容器
docker-compose exec redis redis-cli -a redispass123

# 常用命令
KEYS *                           # 列出所有键
GET key_name                     # 获取值
SET key_name value              # 设置值
HGETALL hash_name               # 获取哈希
LPUSH list_name value           # 推送到列表
INCR counter                     # 增加计数

# 查看黑名单
KEYS "blacklist:*"
GET "blacklist:192.168.1.1"

# 查看请求计数
KEYS "requests:*"
GET "requests:192.168.1.1"

# 清除数据
DEL key_name
FLUSHDB                          # 清空数据库
```

## 📊 监控 APISIX

### 查看 APISIX 指标

```bash
# 获取 APISIX 运行状态
curl http://localhost:9180/apisix/admin/status

# 获取插件列表
curl http://localhost:9180/apisix/admin/plugins/list

# 获取所有路由
curl http://localhost:9180/apisix/admin/routes

# 获取所有上游
curl http://localhost:9180/apisix/admin/upstreams
```

### 在 Grafana 中查看 APISIX 指标

1. 访问 http://localhost:3000 (Grafana)
2. 添加 Prometheus 数据源: http://prometheus:9090
3. 创建仪表板查看 APISIX 性能指标

## 🚀 插件开发工作流

### 完整工作流

```bash
# 1. 启动系统
bash start-docker.sh

# 2. 创建新插件
nano apisix-plugins/new_plugin.lua

# 3. 编写 Lua 代码
# (编辑文件)

# 4. 重启 APISIX 加载插件
docker-compose restart apisix

# 5. 验证插件加载
docker-compose exec apisix curl http://localhost:9180/apisix/admin/plugins/list

# 6. 创建测试路由
curl -X PUT http://localhost:9180/apisix/admin/routes/1 \
  -H 'Content-Type: application/json' \
  -d '{...}'

# 7. 测试路由
curl http://localhost:9080/api/test

# 8. 查看日志
docker-compose logs apisix

# 9. 提交到 Git
git add apisix-plugins/new_plugin.lua
git commit -m "添加新插件"
```

## 🔧 常用 APISIX 命令

### 容器内命令

```bash
# 进入 APISIX 容器
docker-compose exec apisix bash

# 查看 APISIX 版本
apisix version

# 启动 APISIX
apisix start

# 停止 APISIX
apisix stop

# 重新加载配置
apisix reload

# 查看配置
cat /usr/local/apisix/conf/config.yaml

# 查看插件
ls /opt/apisix/plugins/

# 查看日志
tail -f /usr/local/apisix/logs/access.log
```

### Admin API 命令

```bash
# 获取所有插件
curl http://localhost:9180/apisix/admin/plugins/list

# 获取特定插件信息
curl http://localhost:9180/apisix/admin/plugins/cdn_defense

# 更新插件配置
curl -X PATCH http://localhost:9180/apisix/admin/plugins/cdn_defense \
  -H 'Content-Type: application/json' \
  -d '{...}'

# 禁用插件
curl -X DELETE http://localhost:9180/apisix/admin/plugins/cdn_defense
```

## 📚 APISIX 插件开发资源

### 官方文档
- [APISIX 插件开发](https://apisix.apache.org/docs/apisix/plugin-develop/)
- [APISIX Lua API](https://apisix.apache.org/docs/apisix/api/)
- [APISIX 内置插件](https://apisix.apache.org/docs/apisix/plugins/plugin-list/)

### Lua 资源
- [Lua 5.1 手册](https://www.lua.org/manual/5.1/)
- [OpenResty Lua Guide](https://github.com/openresty/lua-nginx-module)

### Redis Lua 库
- [lua-resty-redis](https://github.com/openresty/lua-resty-redis)

## 🎯 快速参考

### 启动容器化环境

```bash
bash start-docker.sh
```

### 开发插件

```bash
# 1. 编辑插件
nano apisix-plugins/my_plugin.lua

# 2. 重启 APISIX
docker-compose restart apisix

# 3. 测试
curl http://localhost:9080/api/test

# 4. 提交
git add apisix-plugins/my_plugin.lua
git commit -m "添加/更新插件"
```

### 查看日志

```bash
docker-compose logs -f apisix
docker-compose logs -f redis
docker-compose logs -f etcd
```

### 进入容器

```bash
docker-compose exec apisix bash       # APISIX
docker-compose exec redis redis-cli   # Redis
docker-compose exec etcd bash         # etcd
```

---

## 总结

✅ **APISIX 插件开发 - 完全容器化**
- 插件位置: `apisix-plugins/`
- 容器自动加载: `/opt/apisix/plugins/`
- 卷挂载: 代码变更自动同步
- Admin API: http://localhost:9180/apisix/admin

✅ **Redis - 完全容器化**
- 端口: 6379
- 密码: redispass123
- 容器名: redis
- CLI 访问: `docker-compose exec redis redis-cli -a redispass123`

✅ **开发工作流**
- 编辑本地文件
- 重启容器加载
- 即时测试和验证
- 提交到 Git

所有开发都在 Docker 容器中进行，确保开发、测试、生产环境完全一致！
