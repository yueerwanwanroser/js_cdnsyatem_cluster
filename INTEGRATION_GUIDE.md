# 全局配置同步集成指南

## 快速开始

本指南说明如何将全局配置同步系统集成到现有的 CDN 防御系统中。

## 1. 依赖安装

```bash
# 更新依赖
pip install -r requirements.txt

# 主要新增依赖
pip install etcd3==0.12.0
```

## 2. 文件概览

| 文件 | 用途 |
|------|------|
| `backend/global_sync_manager.py` | 核心同步引擎（750+ 行）|
| `backend/global_config_api.py` | 全局配置 API 端点（400+ 行）|
| `GLOBAL_CONFIG_SYNC.md` | 完整文档和 API 参考 |
| `demo_global_sync.sh` | 演示脚本 |

## 3. 启动方式

### 3.1 单独运行（开发环境）

```bash
# 终端 1: 启动全局配置 API
cd backend
python global_config_api.py

# 输出应显示:
# INFO:__main__:全局配置同步 API 启动，节点 ID: node-1
# * Running on http://0.0.0.0:5001
```

### 3.2 Docker 方式（生产环境）

更新 `docker/docker-compose.yml`：

```yaml
services:
  # ... 其他服务 ...
  
  defense-api:
    build: 
      context: ..
      dockerfile: docker/Dockerfile.defense-api
    ports:
      - "5000:5000"
    environment:
      - REDIS_HOST=redis
      - ETCD_HOST=etcd
      - ETCD_PORT=2379
      - NODE_ID=node-1
    depends_on:
      - redis
      - etcd
    networks:
      - cdn-defense-network
  
  # 新服务：全局配置 API
  global-config-api:
    build:
      context: ..
      dockerfile: docker/Dockerfile.global-config-api
    ports:
      - "5001:5001"
    environment:
      - ETCD_HOST=etcd
      - ETCD_PORT=2379
      - NODE_ID=node-1
      - GLOBAL_API_PORT=5001
    depends_on:
      - etcd
      - redis
    networks:
      - cdn-defense-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/sync-status"]
      interval: 10s
      timeout: 5s
      retries: 3

  etcd:
    image: bitnami/etcd:3.5
    ports:
      - "2379:2379"
    environment:
      - ETCD_ENABLE_V2=true
      - ALLOW_NONE_AUTHENTICATION=yes
    networks:
      - cdn-defense-network
```

创建 `docker/Dockerfile.global-config-api`：

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend/global_sync_manager.py .
COPY backend/global_config_api.py .

CMD ["python", "global_config_api.py"]
```

启动容器：

```bash
cd docker
docker-compose up -d
```

## 4. 环境变量配置

```bash
# .env 文件
ETCD_HOST=localhost
ETCD_PORT=2379
NODE_ID=node-1
GLOBAL_API_PORT=5001

# Redis (现有系统)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# APISIX (现有系统)
APISIX_HOST=localhost
APISIX_ADMIN_PORT=9180
```

## 5. 核心概念

### 5.1 单一真实源

```
etcd (唯一的配置来源)
  ├── /cdn-defense/config/{tenant_id}    # 租户配置
  ├── /cdn-defense/routes/{route_id}     # 路由定义
  ├── /cdn-defense/ssl/{cert_id}         # SSL 证书
  └── /cdn-defense/versions/{key}        # 版本控制
```

### 5.2 自动同步流程

```
API 修改请求
    ↓
GlobalConfigManager.set_*()  # 写入 etcd
    ↓
etcd watch 事件
    ↓
┌─────────────────┬──────────────┐
↓                 ↓              ↓
Node 缓存      Node 缓存      APISIX 缓存
更新           更新           更新
```

### 5.3 多节点部署

每个节点需要运行一个 `NodeSyncManager`：

```python
# 在 global_config_api.py 中
node_id = os.getenv('NODE_ID', 'node-1')
node_sync_mgr = NodeSyncManager(node_id, etcd_host, etcd_port)
node_sync_mgr.start_sync_daemon()  # 后台同步
```

## 6. API 使用示例

### 6.1 创建租户配置（全局生效）

```bash
curl -X POST http://localhost:5001/global-config/tenant \
  -H "X-Tenant-ID: my-tenant" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "rate_limit": 1000,
      "threat_threshold": 70,
      "enabled_defense": true
    }
  }'
```

**重要**: 此修改立即同步到：
- ✅ etcd 
- ✅ 所有其他节点的缓存
- ✅ APISIX 防御插件

### 6.2 创建路由（自动在 APISIX 中生效）

```bash
curl -X POST http://localhost:5001/global-routes \
  -H "X-Tenant-ID: my-tenant" \
  -H "Content-Type: application/json" \
  -d '{
    "route": {
      "id": "my-api",
      "path": "/api/*",
      "upstream": "http://backend:8080",
      "methods": ["GET", "POST"]
    }
  }'
```

### 6.3 启用防御插件（全局应用）

```bash
curl -X POST http://localhost:5001/defense-plugin/apply \
  -H "X-Tenant-ID: my-tenant" \
  -H "Content-Type: application/json" \
  -d '{
    "route_id": "my-api",
    "defense_config": {
      "enabled": true,
      "threat_threshold": 75,
      "challenge_type": "js"
    }
  }'
```

## 7. 验证部署

### 7.1 检查 etcd 连接

```bash
etcdctl --endpoints=http://localhost:2379 member list
```

### 7.2 查看同步状态

```bash
curl http://localhost:5001/sync-status | jq .
```

**预期输出**:
```json
{
  "node_id": "node-1",
  "sync_status": {
    "total_cached_configs": 3,
    "total_cached_routes": 5,
    "last_sync": "2025-01-15T10:30:45Z",
    "etcd_connected": true
  }
}
```

### 7.3 测试多节点同步

在 Node-2 上运行：

```bash
curl http://node2:5001/sync-status | jq .cache_items
```

应该显示相同的缓存项数量。

## 8. 运行演示脚本

```bash
# 启动所有服务
docker-compose up -d

# 等待服务启动（约 10 秒）
sleep 10

# 运行演示
./demo_global_sync.sh

# 期望输出：
# ✓ 租户配置已创建，存储在 etcd
# ✓ 路由已创建，自动同步到 APISIX 和所有节点
# ✓ SSL 证书已上传，同步到所有节点
# ✓ 防御插件已启用，所有 APISIX 实例自动加载
# ...
```

## 9. 故障排查

### 问题：etcd 连接失败

```
Error: etcd connection refused
```

**解决**:
```bash
# 检查 etcd 状态
docker ps | grep etcd

# 检查 etcd 日志
docker logs etcd

# 重启 etcd
docker-compose restart etcd
```

### 问题：配置未同步

```bash
# 手动刷新节点同步
curl -X POST http://localhost:5001/sync/refresh

# 查看最新状态
curl http://localhost:5001/sync-status
```

### 问题：APISIX 未加载新路由

```bash
# 检查 APISIX 路由
curl http://localhost:9180/apisix/admin/routes

# 验证 etcd 中的路由
etcdctl --endpoints=http://localhost:2379 get /cdn-defense/routes --prefix
```

## 10. 监控和日志

### 10.1 查看同步日志

```bash
# 查看 Node-1 日志
docker logs global-config-api-node-1

# 查看 etcd 活动
etcdctl --endpoints=http://localhost:2379 watch /cdn-defense --prefix
```

### 10.2 监控 API

```bash
# 获取全局监控信息
curl http://localhost:5001/monitor/global-sync | jq .

# 输出示例
{
  "etcd_status": {
    "total_tenants": 3,
    "total_routes": 8,
    "total_ssl_certs": 5
  },
  "node_status": {
    "node_id": "node-1",
    "cache_items": 16,
    "is_syncing": false
  }
}
```

## 11. 性能优化

### 11.1 缓存策略

- 所有配置在节点启动时加载到内存
- 读取时优先使用本地缓存（毫秒级）
- etcd watch 事件触发缓存更新（异步）

### 11.2 扩展到多个节点

```yaml
# docker-compose.yml - 添加更多节点
global-config-api-node-2:
  image: cdn-defense-global-config-api
  environment:
    - NODE_ID=node-2
  # ... 其他配置
  
global-config-api-node-3:
  image: cdn-defense-global-config-api
  environment:
    - NODE_ID=node-3
  # ... 其他配置
```

每个节点会自动同步 etcd 中的所有配置。

## 12. 与现有系统的集成

### 12.1 保持现有 defense_api.py 兼容

旧的 API 端点仍然工作：

```bash
# 旧端点（仍然可用）
curl -X POST http://localhost:5000/config \
  -H "X-Tenant-ID: my-tenant"
```

### 12.2 新的全局 API

```bash
# 新端点（推荐）
curl -X POST http://localhost:5001/global-config/tenant \
  -H "X-Tenant-ID: my-tenant"
```

### 12.3 迁移策略

1. **第一阶段**: 新部署使用 `global_config_api.py`
2. **第二阶段**: 现有系统中的 `defense_api.py` 添加到 etcd 同步
3. **第三阶段**: 完全迁移到全局配置 API

## 13. 总结

全局配置同步系统提供：

| 特性 | 描述 |
|------|------|
| **单一真实源** | etcd 存储所有配置 |
| **自动同步** | watch 事件推送更新到所有节点 |
| **即时生效** | 无需重启任何服务 |
| **多节点支持** | 自动扩展到任意数量节点 |
| **APISIX 集成** | 路由和插件自动加载 |
| **高可用** | etcd 集群支持，节点故障隔离 |

**核心优势**: 修改一处配置，整个系统自动更新！

这正是对您的问题 "后台每个修改参数只管理自己的一亩三分地，不能说修改了" 的完整解决方案。
