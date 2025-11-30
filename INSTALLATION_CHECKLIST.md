# CDN 防御系统 - 安装和验证清单

## ✅ 系统要求检查

- [ ] Docker 已安装 (版本 >= 20.10)
  ```bash
  docker --version
  ```

- [ ] Docker Compose 已安装 (版本 >= 2.0)
  ```bash
  docker-compose --version
  ```

- [ ] Python 3.8+ 已安装
  ```bash
  python3 --version
  ```

- [ ] 至少 8GB 内存可用
- [ ] 至少 20GB 磁盘空间可用
- [ ] 端口 9080, 9180, 5000, 5001, 6379, 3000, 9090 未被占用

## 📦 部署步骤

### 1. 项目准备

- [ ] 进入项目目录
  ```bash
  cd /home/alana/azuredev-cd81/cdn-defense-system
  ```

- [ ] 检查文件完整性
  ```bash
  ls -la *.py *.sh *.md requirements.txt
  ls -la apisix-plugins/ backend/ js-defense/ docker/
  ```

- [ ] 赋予脚本执行权限
  ```bash
  chmod +x deploy.sh stop.sh quicktest.sh
  ```

### 2. 启动系统

- [ ] 执行部署脚本
  ```bash
  ./deploy.sh
  ```

- [ ] 等待所有容器启动 (2-3 分钟)

- [ ] 检查容器状态
  ```bash
  docker-compose -f docker/docker-compose.yml ps
  ```

  预期输出:
  ```
  NAME                    STATUS
  cdn-defense-redis      Up
  cdn-defense-apisix     Up
  cdn-defense-etcd       Up
  cdn-defense-api        Up
  cdn-defense-api-2      Up
  cdn-defense-prometheus Up
  cdn-defense-grafana    Up
  ```

### 3. 验证服务

#### 3.1 Redis 连接

- [ ] 检查 Redis 运行状态
  ```bash
  docker exec cdn-defense-redis redis-cli ping
  ```
  
  预期: `PONG`

#### 3.2 APISIX 网关

- [ ] 检查 APISIX 管理 API
  ```bash
  curl -s http://localhost:9180/apisix/admin/routes | head -20
  ```

- [ ] 验证网关可访问
  ```bash
  curl -i http://localhost:9080/apisix/status
  ```

#### 3.3 防御 API

- [ ] 检查 API 健康状态
  ```bash
  curl http://localhost:5000/health
  ```

  预期输出:
  ```json
  {"status":"healthy","node_id":"node-1",...}
  ```

- [ ] 检查节点2状态
  ```bash
  curl http://localhost:5001/health
  ```

#### 3.4 监控系统

- [ ] 访问 Prometheus
  ```
  http://localhost:9090
  ```
  检查: 指标已收集

- [ ] 访问 Grafana
  ```
  http://localhost:3000
  ```
  登录: admin/admin
  检查: 仪表板加载正常

### 4. 快速功能测试

- [ ] 运行快速测试脚本
  ```bash
  ./quicktest.sh
  ```

  检查所有测试项是否通过:
  - [ ] 健康检查
  - [ ] 正常请求
  - [ ] 黑名单
  - [ ] 白名单
  - [ ] 配置管理
  - [ ] 统计接口
  - [ ] 日志接口
  - [ ] 并发请求

### 5. 创建测试租户

- [ ] 创建租户
  ```bash
  python3 admin_cli.py tenant create --id test-tenant
  ```

- [ ] 验证租户创建
  ```bash
  python3 admin_cli.py tenant list
  ```

### 6. 测试防御功能

- [ ] 发送测试请求
  ```bash
  curl -X POST http://localhost:5000/analyze \
    -H "Content-Type: application/json" \
    -H "X-Tenant-ID: test-tenant" \
    -d '{
      "request": {
        "request_id": "test-001",
        "timestamp": '$(date +%s)',
        "client_ip": "192.168.1.100",
        "user_agent": "Mozilla/5.0",
        "path": "/api/test",
        "method": "GET",
        "headers": {},
        "payload_size": 1024,
        "user_id": "test-user"
      }
    }'
  ```

- [ ] 验证响应包含防御决策
  - [ ] `allow` 字段存在
  - [ ] `threat_score` 字段存在
  - [ ] `action` 字段存在

### 7. 测试黑名单功能

- [ ] 添加 IP 到黑名单
  ```bash
  python3 admin_cli.py blacklist add --tenant-id test-tenant --ip 192.168.1.200
  ```

- [ ] 查看黑名单
  ```bash
  python3 admin_cli.py blacklist list --tenant-id test-tenant
  ```

- [ ] 验证 IP 在列表中

### 8. 测试白名单功能

- [ ] 添加 IP 到白名单
  ```bash
  python3 admin_cli.py whitelist add --tenant-id test-tenant --ip 10.0.0.1
  ```

- [ ] 查看白名单
  ```bash
  python3 admin_cli.py whitelist list --tenant-id test-tenant
  ```

- [ ] 验证 IP 在列表中

### 9. 测试配置管理

- [ ] 获取配置
  ```bash
  python3 admin_cli.py config get --tenant-id test-tenant
  ```

- [ ] 更新配置
  ```bash
  python3 admin_cli.py config set --tenant-id test-tenant \
    --key rate_limit_per_minute --value 150
  ```

- [ ] 验证配置已更新

### 10. 查看统计信息

- [ ] 获取统计数据
  ```bash
  python3 admin_cli.py stats --tenant-id test-tenant
  ```

  验证包含:
  - [ ] total_requests
  - [ ] blocked
  - [ ] allowed
  - [ ] avg_threat_score
  - [ ] top_ips

### 11. 查看日志

- [ ] 获取防御日志
  ```bash
  python3 admin_cli.py logs --tenant-id test-tenant --limit 10
  ```

  验证日志包含:
  - [ ] timestamp
  - [ ] request_id
  - [ ] client_ip
  - [ ] threat_score
  - [ ] decision

### 12. 性能测试

- [ ] 运行单元测试
  ```bash
  python3 test_defense_system.py --unit
  ```

  验证所有测试通过

- [ ] 运行性能基准测试
  ```bash
  python3 test_defense_system.py --benchmark
  ```

  验证:
  - [ ] 吞吐量 > 500 req/s
  - [ ] 平均延迟 < 100ms
  - [ ] P99 延迟 < 300ms

## 🔍 故障诊断

### 容器无法启动

```bash
# 检查日志
docker logs cdn-defense-api
docker logs cdn-defense-apisix
docker logs cdn-defense-redis

# 重启容器
docker-compose -f docker/docker-compose.yml restart

# 完全重建
docker-compose -f docker/docker-compose.yml down
docker-compose -f docker/docker-compose.yml up -d
```

### API 无响应

```bash
# 检查容器状态
docker-compose -f docker/docker-compose.yml ps

# 检查网络连接
docker network inspect cdn-defense-network

# 查看API日志
docker logs -f cdn-defense-api
```

### Redis 连接错误

```bash
# 测试Redis连接
docker exec cdn-defense-redis redis-cli ping

# 查看Redis日志
docker logs cdn-defense-redis

# 检查Redis内存
docker exec cdn-defense-redis redis-cli info memory
```

### 性能问题

```bash
# 检查容器资源使用
docker stats

# 查看慢查询日志
docker exec cdn-defense-api tail -f /var/log/*.log

# 检查Redis连接池
docker exec cdn-defense-redis redis-cli INFO clients
```

## 📋 检查清单总结

### 基础设施 (Infrastructure)
- [ ] Docker 运行正常
- [ ] Docker Compose 可用
- [ ] 网络配置正确
- [ ] 端口未被占用
- [ ] 磁盘空间充足
- [ ] 内存充足

### 容器服务 (Containers)
- [ ] Redis 容器运行
- [ ] APISIX 容器运行
- [ ] etcd 容器运行
- [ ] 防御 API 节点1 运行
- [ ] 防御 API 节点2 运行
- [ ] Prometheus 容器运行
- [ ] Grafana 容器运行

### API 功能 (API Functions)
- [ ] 健康检查端点可用
- [ ] 请求分析端点可用
- [ ] 黑名单端点可用
- [ ] 白名单端点可用
- [ ] 配置端点可用
- [ ] 统计端点可用
- [ ] 日志端点可用

### 管理工具 (Management)
- [ ] 租户管理工具可用
- [ ] 黑名单管理工具可用
- [ ] 白名单管理工具可用
- [ ] 配置管理工具可用
- [ ] 统计查询工具可用
- [ ] 日志查询工具可用

### 防御功能 (Defense Functions)
- [ ] 请求分析正常
- [ ] 威胁评分计算
- [ ] 黑名单拦截
- [ ] 白名单放行
- [ ] 速率限制生效
- [ ] 异常检测工作
- [ ] 日志记录完整

### 监控系统 (Monitoring)
- [ ] Prometheus 收集指标
- [ ] Grafana 显示仪表板
- [ ] 系统指标可见
- [ ] 防御指标可见
- [ ] 性能指标可见

### 文档和工具 (Documentation)
- [ ] README.md 可读
- [ ] QUICKSTART.md 可用
- [ ] PROJECT_SUMMARY.md 完整
- [ ] config_example.py 有效
- [ ] 测试脚本可执行
- [ ] 管理脚本可用

## ✅ 验证完成

所有检查项完成后，系统已准备好投入使用！

```bash
# 最后的验证
./quicktest.sh

# 如果所有测试通过，系统已完全就绪
echo "系统已准备好！🎉"
```

## 🚀 下一步

- [ ] 配置 SSL/TLS (生产环境)
- [ ] 设置备份计划
- [ ] 配置监控告警
- [ ] 优化性能参数
- [ ] 部署到多个节点
- [ ] 设置容灾切换

---

**最后更新**: 2024年11月30日  
**预计完成时间**: 15-20 分钟  
**难度等级**: ⭐☆☆☆☆ 容易
