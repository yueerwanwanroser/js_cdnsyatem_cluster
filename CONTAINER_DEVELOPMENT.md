# 容器化开发指南

## 概述

完整的 Docker 容器化开发环境，所有服务包括数据库、缓存、网关、后端、前端都运行在容器中。

## 架构

```
┌─────────────────────────────────────────────────────┐
│              Nginx (前端生产环境)                    │
│              Port: 80                               │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│            Django REST API                          │
│            Port: 8000                              │
│  ┌──────────────────────────────────────────┐      │
│  │ - PostgreSQL 连接                        │      │
│  │ - Redis 缓存                             │      │
│  │ - etcd 全局配置同步                      │      │
│  └──────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────┘
            │              │              │
            ▼              ▼              ▼
     ┌──────────┐   ┌──────────┐   ┌──────────┐
     │PostgreSQL│   │  Redis   │   │  etcd    │
     │Port 5432 │   │Port 6379 │   │Port 2379 │
     └──────────┘   └──────────┘   └──────────┘

附加服务:
     ┌──────────┐   ┌────────────┐   ┌──────────┐
     │  APISIX  │   │ Prometheus │   │ Grafana  │
     │Port 9080 │   │ Port 9090  │   │ Port 3000│
     └──────────┘   └────────────┘   └──────────┘
```

## 快速开始

### 1. 前置条件

- ✅ Docker (20.10+)
- ✅ Docker Compose (2.0+)
- ✅ 系统要求: 4GB+ RAM, 20GB+ 磁盘空间

```bash
# 检查版本
docker --version
docker-compose --version
```

### 2. 启动所有服务

```bash
# 进入项目根目录
cd cdn-defense-system

# 启动所有容器
bash docker-compose-dev.sh start

# 或使用 docker-compose 直接启动
docker-compose up -d
```

输出示例:
```
Creating cdn-postgres ... done
Creating cdn-redis    ... done
Creating cdn-etcd     ... done
Creating cdn-apisix   ... done
Creating cdn-django   ... done
Creating cdn-frontend ... done
```

### 3. 验证服务

```bash
# 查看服务状态
bash docker-compose-dev.sh status

# 查看访问信息
bash docker-compose-dev.sh access
```

## 服务访问

### 后端 API

| 服务 | 地址 | 说明 |
|-----|-----|------|
| API 端点 | http://localhost:8000 | Django REST API |
| API 文档 | http://localhost:8000/api/docs/ | Swagger 自动生成的文档 |
| Admin 后台 | http://localhost:8000/admin/ | Django 后台管理 |
| 同步状态 | http://localhost:8000/api/v1/sync-status/ | 全局同步状态 |

**默认凭证**: `admin` / `admin123`

### 前端

| 环境 | 地址 | 说明 |
|-----|-----|------|
| 生产环境 | http://localhost | Nginx 提供的生产构建 |
| 开发环境 | http://localhost:5173 | Vite 开发服务器 (可选) |

### 基础设施

| 服务 | 地址 | 说明 |
|-----|-----|------|
| APISIX 管理 | http://localhost:9180/apisix/admin | API 网关管理界面 |
| etcd 监控 | http://localhost:2379 | 分布式配置存储 |
| Redis | localhost:6379 | 缓存服务 |
| PostgreSQL | localhost:5432 | 数据库服务 |

### 监控

| 服务 | 地址 | 凭证 |
|-----|-----|------|
| Prometheus | http://localhost:9090 | 无需认证 |
| Grafana | http://localhost:3000 | admin / grafana123 |

## 常用命令

### 基本操作

```bash
# 启动所有服务
bash docker-compose-dev.sh start

# 停止所有服务
bash docker-compose-dev.sh stop

# 重启所有服务
bash docker-compose-dev.sh restart

# 查看服务状态
bash docker-compose-dev.sh status

# 查看实时日志
bash docker-compose-dev.sh logs

# 构建镜像 (修改后)
bash docker-compose-dev.sh build
```

### 进入容器

```bash
# 进入 Django 容器
bash docker-compose-dev.sh shell django

# 进入前端容器
bash docker-compose-dev.sh shell frontend

# 连接到 PostgreSQL
bash docker-compose-dev.sh db-shell

# 连接到 Redis
bash docker-compose-dev.sh redis-cli

# 进入 etcd 容器
bash docker-compose-dev.sh shell etcd
```

### 直接命令

```bash
# 查看 Django 日志
docker-compose logs django

# 查看前端日志
docker-compose logs frontend

# 执行 Django 管理命令
docker-compose exec django python manage.py createsuperuser

# 运行 Django 迁移
docker-compose exec django python manage.py migrate

# 检查容器资源使用
docker stats

# 完全清理 (删除卷和网络)
bash docker-compose-dev.sh clean
```

## 开发工作流

### 修改后端代码

1. 编辑 `backend/` 中的 Python 文件
2. 代码变更自动同步到容器 (因为 volume 挂载)
3. Django 开发服务器会自动重载
4. 访问 API 查看变更

```bash
# 查看后端日志，确认变更已加载
docker-compose logs django
```

### 修改前端代码 (开发环境)

1. 使用开发服务器:
```bash
# 启动前端开发容器
docker-compose up frontend-dev -d

# 访问 http://localhost:5173
```

2. 代码变更会自动热重载
3. 查看变更效果

### 修改前端代码 (生产环境)

1. 编辑 `frontend/` 中的代码
2. 重新构建前端容器:
```bash
docker-compose build frontend
docker-compose up frontend -d
```

3. 访问 http://localhost 查看变更

### 数据库操作

```bash
# 进入 PostgreSQL
docker-compose exec postgres psql -U cdnuser -d cdn_defense

# 常用命令
\dt              # 列出所有表
\d table_name    # 查看表结构
SELECT * FROM ...;
```

### 缓存操作

```bash
# 进入 Redis CLI
docker-compose exec redis redis-cli -a redispass123

# 常用命令
KEYS *
GET key_name
DEL key_name
FLUSHDB          # 清空当前数据库
```

## 调试

### 查看实时日志

```bash
# 所有服务
docker-compose logs -f

# 特定服务
docker-compose logs -f django
docker-compose logs -f frontend
docker-compose logs -f postgres

# 最后 100 行
docker-compose logs --tail=100 django
```

### 检查网络连接

```bash
# 进入 Django 容器
docker-compose exec django bash

# 测试连接
ping postgres
ping redis
ping etcd
```

### 查看资源使用

```bash
# 容器统计
docker-compose stats

# 镜像大小
docker images | grep cdn

# 卷大小
docker volume ls
docker volume inspect cdn-defense-system_postgres_data
```

## 环境变量

编辑 `docker-compose.yml` 中的环境变量:

```yaml
environment:
  DEBUG: "False"                     # 生产模式
  ALLOWED_HOSTS: "*"                # 允许的主机
  SECRET_KEY: "your-secret-key"     # Django 密钥
  DB_NAME: cdn_defense              # 数据库名
  REDIS_URL: redis://...            # Redis 连接
  ETCD_HOST: etcd                   # etcd 主机
```

## 性能优化

### 1. 资源限制

编辑 `docker-compose.yml`:

```yaml
services:
  django:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### 2. 日志大小控制

```yaml
services:
  django:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 3. 镜像优化

- 使用 Alpine 基础镜像
- 多阶段构建
- 最小化层数
- 清理包管理器缓存

## 生产部署

### 1. 更新环境变量

```bash
# .env 文件
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
SECRET_KEY=your-secure-random-key
DB_PASSWORD=secure-password
REDIS_PASSWORD=secure-password
```

### 2. 使用生产数据库

```yaml
postgres:
  environment:
    POSTGRES_PASSWORD: ${DB_PASSWORD}
```

### 3. 使用 Traefik 反向代理

```yaml
services:
  frontend:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`yourdomain.com`)"
      - "traefik.http.services.frontend.loadbalancer.server.port=80"
```

### 4. 备份和恢复

```bash
# 备份数据库
docker-compose exec postgres pg_dump -U cdnuser cdn_defense > backup.sql

# 恢复数据库
docker-compose exec -T postgres psql -U cdnuser cdn_defense < backup.sql

# 备份卷
docker run --rm -v cdn-defense-system_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres_backup.tar.gz -C /data .
```

## 故障排除

### 容器无法启动

```bash
# 查看错误日志
docker-compose logs django

# 检查镜像是否构建成功
docker images | grep cdn

# 重新构建
docker-compose build --no-cache django
```

### 数据库连接失败

```bash
# 检查 PostgreSQL 日志
docker-compose logs postgres

# 测试连接
docker-compose exec django nc -zv postgres 5432
```

### 前端无法加载

```bash
# 检查 Nginx 日志
docker-compose logs frontend

# 检查网络
docker network ls
docker network inspect cdn-defense-system_cdn-network
```

### 性能缓慢

```bash
# 检查资源
docker stats

# 检查磁盘空间
docker system df

# 清理未使用的镜像和卷
docker system prune -a --volumes
```

## 清理和重置

### 完全重置开发环境

```bash
# 停止和删除所有容器、卷、网络
bash docker-compose-dev.sh clean

# 或手动操作
docker-compose down -v
docker system prune -a --volumes
```

### 删除特定容器

```bash
# 删除 Django 容器
docker-compose rm django

# 删除卷
docker volume rm cdn-defense-system_postgres_data
```

## 扩展和集群

### 多副本部署

```yaml
services:
  django:
    deploy:
      replicas: 3
```

### 使用 Docker Swarm

```bash
# 初始化 Swarm
docker swarm init

# 部署堆栈
docker stack deploy -c docker-compose.yml cdn
```

### 使用 Kubernetes

转换 Docker Compose 为 Kubernetes:

```bash
# 安装工具
pip install kompose

# 转换
kompose convert -f docker-compose.yml
```

## 相关文档

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 参考](https://docs.docker.com/compose/compose-file/)
- [Django 部署](https://docs.djangoproject.com/en/4.2/howto/deployment/)
- [PostgreSQL Docker](https://hub.docker.com/_/postgres)

## 获取帮助

```bash
# 显示所有命令
bash docker-compose-dev.sh help

# 查看服务状态
bash docker-compose-dev.sh status

# 查看访问信息
bash docker-compose-dev.sh access
```

---

**现在所有开发都在容器中完成，确保环境一致性和可重复性！** 🎉
