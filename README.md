# CDN 防御系统 (多节点集群版本)

基于 Django + APISIX 的高性能 CDN 防御系统，支持多节点集群、多用户隔离、JS 防御、全局配置同步等功能。

**🎉 现已完全容器化！所有服务（后端、前端、数据库、缓存、网关、监控）都运行在 Docker 容器中。**

## 🎯 核心功能

### 1. 防御引擎
- **流量分析**: 实时分析请求特征和异常
- **威胁检测**: 识别 DDoS、CC 攻击、SQL 注入、XSS 等威胁
- **异常检测**: 基于机器学习的异常模式识别
- **速率限制**: 多层级速率限制策略
- **黑/白名单**: 灵活的黑名单和白名单管理

### 2. JS 防御
- **浏览器指纹**: Canvas、WebGL、设备特征识别
- **验证码挑战**: 支持数学、拼图、行为验证码
- **机器人检测**: 识别无头浏览器和自动化工具
- **设备信任**: 可信设备缓存和管理

### 3. 多节点集群
- **分布式防御**: 支持多个防御节点协同工作
- **全局配置中心**: etcd 实现全局配置管理和同步
- **自动同步**: Django signals 自动同步配置变更到 etcd
- **负载均衡**: APISIX 网关负载均衡

### 4. 多用户隔离
- **租户模型**: 完整的租户隔离和管理
- **数据隔离**: 每个租户的数据完全隔离
- **配置隔离**: 租户级别的防御策略配置
- **审计日志**: 租户级别的完整操作日志

### 5. 容器化部署
- **一键启动**: `bash start-docker.sh` 启动所有服务
- **开发/生产分离**: 支持开发和生产环境
- **健康检查**: 自动检查和重启故障容器
- **卷挂载**: 实时代码同步，无需重启

## 🚀 快速开始 (3 步)

### 方式 1: 一键启动 (推荐) ⭐

```bash
# 进入项目目录
cd cdn-defense-system

# 一键启动所有服务
bash start-docker.sh
```

**完成！所有服务已启动，访问以下地址:**

| 服务 | 地址 |
|-----|-----|
| 🌐 前端 | http://localhost |
| 🔧 API | http://localhost:8000 |
| 📖 文档 | http://localhost:8000/api/docs/ |
| 🎛️ Admin | http://localhost:8000/admin/ (admin/admin123) |
| 📊 Grafana | http://localhost:3000 (admin/grafana123) |

### 方式 2: 手动启动

```bash
# 启动所有容器
docker-compose up -d

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 方式 3: 使用管理脚本

```bash
# 启动
bash docker-compose-dev.sh start

# 停止
bash docker-compose-dev.sh stop

# 查看帮助
bash docker-compose-dev.sh help
```

## 📋 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Nginx (前端)                           │
│                    Port: 80 (生产)                          │
│                   Port: 5173 (开发)                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │   Django REST API (8000)     │
        │  ┌─────────────────────────┐ │
        │  │ - 7 个数据库模型 (ORM)   │ │
        │  │ - 15+ REST 端点          │ │
        │  │ - 自动 etcd 同步 (信号)  │ │
        │  │ - Admin 后台             │ │
        │  └─────────────────────────┘ │
        └──────────┬────────────────────┘
                   │
     ┌─────────────┼─────────────┐
     ▼             ▼             ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│PostgreSQL│ │ Redis    │ │ etcd     │
│(5432)    │ │ (6379)   │ │ (2379)   │
│ ORM 数据  │ │ 缓存     │ │ 配置中心  │
└──────────┘ └──────────┘ └──────────┘

┌────────────────────────────────────┐
│ APISIX (9080) - API 网关          │
│  - 路由管理                        │
│  - 防御插件 (Lua)                  │
│  - 限流/认证                       │
└────────────────────────────────────┘

┌────────────────────────────────────┐
│ 监控                              │
│ - Prometheus (9090)               │
│ - Grafana (3000)                  │
└────────────────────────────────────┘
```


# 启动系统
./deploy.sh
```

### 2. 验证部署

```bash
# 检查容器状态
docker-compose -f docker/docker-compose.yml ps

# 检查防御 API 健康状态
curl http://localhost:5000/health

# 检查 Redis 连接
redis-cli -h 127.0.0.1 ping
```

## 📊 管理接口

### 创建租户

```bash
python admin_cli.py tenant create --id tenant-001
```

### 添加到黑名单

```bash
python admin_cli.py blacklist add --tenant-id tenant-001 --ip 192.168.1.100 --duration 3600
```

### 添加到白名单

```bash
python admin_cli.py whitelist add --tenant-id tenant-001 --ip 192.168.1.50
```

### 查看统计信息

```bash
python admin_cli.py stats --tenant-id tenant-001
```

### 查看防御日志

```bash
python admin_cli.py logs --tenant-id tenant-001 --limit 50
```

### 获取配置

```bash
python admin_cli.py config get --tenant-id tenant-001
```

### 更新配置

```bash
python admin_cli.py config set --tenant-id tenant-001 --key rate_limit_per_minute --value 200
```

## 🔌 API 接口

### 分析请求

```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: tenant-001" \
  -d '{
    "request": {
      "request_id": "req-001",
      "timestamp": 1234567890,
      "client_ip": "192.168.1.100",
      "user_agent": "Mozilla/5.0",
      "path": "/api/data",
      "method": "GET",
      "headers": {},
      "payload_size": 1024,
      "user_id": "user-123"
    }
  }'
```

响应示例:
```json
{
  "request_id": "req-001",
  "allow": true,
  "action": "allow",
  "threat_level": "LOW",
  "threat_score": 10.5,
  "reason": "通过防御检查",
  "require_js_challenge": false,
  "block_duration": 0
}
```

### 获取统计信息

```bash
curl -X GET http://localhost:5000/statistics \
  -H "X-Tenant-ID: tenant-001"
```

### 获取黑名单

```bash
curl -X GET http://localhost:5000/blacklist \
  -H "X-Tenant-ID: tenant-001"
```

### 获取日志

```bash
curl -X GET "http://localhost:5000/logs?limit=100" \
  -H "X-Tenant-ID: tenant-001"
```

## ⚙️ APISIX 网关配置

### 注册防御插件到路由

```bash
# 配置 etcd
curl -X PUT http://localhost:2379/v3/kv/put \
  -H "Content-Type: application/json" \
  -d '{
    "key": "L2Fwc2l4L3JvdXRlcy8x",
    "value": "{...}"
  }'
```

### 示例路由配置

```json
{
  "uri": "/api/*",
  "name": "defended-api",
  "plugins": {
    "cdn-defense": {
      "defense_engine_url": "http://defense-api:5000",
      "redis_host": "redis",
      "redis_port": 6379,
      "tenant_id": "tenant-001",
      "enable_js_challenge": true
    }
  },
  "upstream": {
    "type": "roundrobin",
    "nodes": {
      "127.0.0.1:8000": 1
    }
  }
}
```

## 📈 监控和可视化

### Prometheus
- URL: http://localhost:9090
- 指标采集间隔: 15 秒

### Grafana
- URL: http://localhost:3000
- 默认账号: admin/admin
- 已配置 Prometheus 数据源

### 关键指标

```
- cdn_defense_requests_total       # 总请求数
- cdn_defense_blocked_total        # 被阻止的请求数
- cdn_defense_threat_score         # 威胁分数
- cdn_defense_processing_time      # 处理时间
- cdn_defense_blacklist_size       # 黑名单大小
```

## 🔐 安全配置

### 防御策略示例

```python
config = {
    'rate_limit_per_minute': 100,      # 每分钟请求限制
    'rate_limit_per_hour': 10000,      # 每小时请求限制
    'js_challenge_threshold': 30,      # JS 挑战威胁分数阈值
    'block_threshold': 70,              # 阻止威胁分数阈值
    'bot_detection_enabled': 'true',   # 启用机器人检测
    'anomaly_detection_enabled': 'true' # 启用异常检测
}
```

### 黑名单持续时间

```bash
# 临时黑名单 (1 小时)
python admin_cli.py blacklist add --tenant-id tenant-001 --ip 192.168.1.100 --duration 3600

# 永久黑名单 (指定很长的时间)
python admin_cli.py blacklist add --tenant-id tenant-001 --ip 192.168.1.100 --duration 31536000
```

## 📝 日志

### 日志位置

- APISIX 日志: `/var/log/apisix/access.log`
- 防御 API 日志: `docker logs cdn-defense-api`
- Redis 日志: `docker logs cdn-defense-redis`

### 查看日志

```bash
# 实时查看防御 API 日志
docker logs -f cdn-defense-api

# 查看 APISIX 日志
docker logs -f cdn-defense-apisix

# 查看 Redis 日志
docker logs -f cdn-defense-redis
```

## 🛠️ 故障排查

### Redis 连接失败

```bash
# 检查 Redis 状态
docker exec cdn-defense-redis redis-cli ping

# 检查网络连接
docker exec cdn-defense-api ping redis
```

### APISIX 插件未加载

```bash
# 检查插件日志
docker logs cdn-defense-apisix | grep cdn-defense

# 重启 APISIX
docker-compose -f docker/docker-compose.yml restart apisix
```

### 防御 API 无法访问

```bash
# 检查容器状态
docker ps | grep defense-api

# 检查日志
docker logs cdn-defense-api

# 重启服务
docker-compose -f docker/docker-compose.yml restart defense-api defense-api-2
```

## 📦 项目结构

```
cdn-defense-system/
├── apisix-plugins/           # APISIX 网关插件
│   └── cdn_defense.lua      # 主防御插件
├── backend/                  # 防御引擎后端
│   ├── defense_engine.py    # 防御引擎核心
│   └── defense_api.py       # 防御 API 服务
├── js-defense/              # JS 防御模块
│   └── js_defense.py        # 浏览器指纹、验证码
├── monitoring/              # 监控配置
├── docker/                  # Docker 配置
│   ├── docker-compose.yml  # Docker Compose 编排
│   ├── Dockerfile.defense-api
│   ├── apisix_config.yaml
│   └── prometheus.yml
├── admin_cli.py             # 管理命令行工具
├── deploy.sh               # 部署脚本
├── requirements.txt        # Python 依赖
└── README.md              # 本文件
```

## 🔄 集群同步机制

### 黑名单同步

```
节点1 → Redis → 节点2 (Pub/Sub)
```

所有节点订阅 `defense:events` 频道，任何黑名单更新都会自动同步。

### 配置同步

```
管理员更新配置 → Redis hash → 所有节点读取
```

节点启动或定期检查 `defense:config` 中的配置。

## 🚨 威胁分数说明

- **0-30**: 低风险 (允许)
- **30-50**: 中风险 (JS 挑战)
- **50-70**: 高风险 (限流)
- **70+**: 严重风险 (阻止)

## 📞 技术支持

如有问题，请检查日志并查看故障排查部分。

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**最后更新**: 2024年11月30日
