# Django 版 CDN 防御系统 - 快速开始

## 为什么选择 Django？

✅ **开发速度快** - Django 自带 ORM、admin、认证系统  
✅ **功能完整** - 内置数据库、缓存、信号系统  
✅ **前端友好** - 自带 CORS、DRF（Django REST Framework）  
✅ **易于维护** - 大量第三方包和工具链  
✅ **前端集成简单** - 与 Vue/React 无缝配合  

## 快速开始 (3 步)

### 步骤 1: 安装依赖和初始化

```bash
cd cdn-defense-system
bash start_django.sh
```

**自动完成**:
- ✅ 安装所有 Python 依赖
- ✅ 初始化数据库
- ✅ 创建超级用户 (admin/admin123)
- ✅ 启动开发服务器

### 步骤 2: 访问后台管理

打开浏览器访问: http://localhost:8000/admin/

**后台功能**:
- 🔧 租户管理
- 🛣️ 路由管理
- 🔒 SSL 证书管理
- 🛡️ 防御策略管理
- 📊 同步日志查询

### 步骤 3: 使用 REST API

所有功能都通过 API 可用，前端可以直接调用：

```javascript
// 创建租户
POST http://localhost:8000/api/v1/config/tenant/
{
  "tenant": 1,
  "rate_limit": 1000,
  "threat_threshold": 70
}

// 创建路由
POST http://localhost:8000/api/v1/routes/
{
  "route_id": "api-1",
  "tenant": 1,
  "path": "/api/*",
  "upstream": "http://backend:8080"
}

// 应用防御策略
POST http://localhost:8000/api/v1/defense-plugin/apply_to_route/
{
  "route_id": "api-1",
  "defense_config": {"threat_threshold": 75}
}
```

## API 文档

### 自动生成的 API 文档

访问: http://localhost:8000/api/docs/

**Swagger UI 展示所有端点**：
- 完整的 API 参考
- 可直接测试
- 自动生成

### 核心 API 端点

#### 租户配置管理
```
GET    /api/v1/config/tenant/           # 列出所有配置
POST   /api/v1/config/tenant/           # 创建配置
GET    /api/v1/config/tenant/{id}/      # 获取配置
PUT    /api/v1/config/tenant/{id}/      # 更新配置
DELETE /api/v1/config/tenant/{id}/      # 删除配置
```

#### 路由管理
```
GET    /api/v1/routes/                  # 列出所有路由
POST   /api/v1/routes/                  # 创建路由
GET    /api/v1/routes/{id}/             # 获取路由
PUT    /api/v1/routes/{id}/             # 更新路由
DELETE /api/v1/routes/{id}/             # 删除路由
```

#### SSL 证书管理
```
GET    /api/v1/ssl/                     # 列出所有证书
POST   /api/v1/ssl/                     # 上传证书
GET    /api/v1/ssl/{id}/                # 获取证书
PUT    /api/v1/ssl/{id}/                # 更新证书
DELETE /api/v1/ssl/{id}/                # 删除证书
```

#### 防御策略管理
```
GET    /api/v1/defense-plugin/          # 列出所有策略
POST   /api/v1/defense-plugin/          # 创建策略
POST   /api/v1/defense-plugin/apply_to_route/  # 应用到路由
```

#### 监控和诊断
```
GET    /api/v1/sync-status/             # 同步状态
GET    /api/v1/monitor/global-sync/     # 全局监控
```

## 项目结构

```
cdn-defense-system/
├── backend/
│   ├── config/              # Django 项目配置
│   │   ├── __init__.py
│   │   ├── settings.py      # Django 设置
│   │   ├── urls.py          # URL 路由
│   │   └── wsgi.py          # WSGI 应用
│   ├── defense/             # CDN 防御应用
│   │   ├── models.py        # 数据库模型
│   │   ├── views.py         # API 视图
│   │   ├── serializers.py   # 数据序列化
│   │   ├── services.py      # 业务逻辑
│   │   ├── signals.py       # 自动同步
│   │   └── admin.py         # 后台管理
│   ├── manage.py            # Django 管理脚本
│   ├── global_sync_manager.py    # etcd 同步器
│   └── global_config_api.py      # 旧版 API (可选)
├── start_django.sh          # 启动脚本
├── requirements.txt         # Python 依赖
└── ...
```

## 数据库模型

### Tenant (租户)
```python
- tenant_id: 唯一标识符
- name: 显示名称
- is_active: 是否激活
- created_at, updated_at: 时间戳
```

### TenantConfig (租户配置)
```python
- tenant: 外键关联
- rate_limit: 速率限制
- threat_threshold: 威胁阈值
- enabled_defense: 是否启用防御
- js_challenge: 是否启用 JS 挑战
- bot_detection: 是否检测机器人
- version: 版本号
```

### Route (路由)
```python
- route_id: 唯一标识符
- tenant: 租户关联
- path: 路由路径
- upstream: 上游地址
- methods: 允许的方法
- enabled: 是否启用
- plugins: 应用的插件
- version: 版本号
```

### SSLCertificate (SSL 证书)
```python
- cert_id: 唯一标识符
- tenant: 租户关联
- domain: 域名
- cert: 证书内容
- key: 私钥
- expires_at: 过期时间
```

### DefensePolicy (防御策略)
```python
- route: 路由关联
- enabled: 是否启用
- threat_threshold: 威胁阈值
- challenge_type: 挑战类型 (js/captcha/fingerprint)
- js_fingerprint: 是否使用 JS 指纹
- rate_limit: 速率限制
- version: 版本号
```

## 自动同步到 etcd

Django 模型变更时自动同步到 etcd：

1. **保存到数据库** → Django ORM
2. **自动触发信号** → `post_save` 信号
3. **同步到 etcd** → GlobalConfigManager
4. **推送到其他节点** → etcd watch 事件

这样确保所有数据源一致：
- Django 数据库 (本地)
- etcd (全局)
- 其他节点缓存 (自动同步)

## 前端集成 (Vue 3 示例)

```javascript
// api.js
import axios from 'axios'

const API_BASE = 'http://localhost:8000/api/v1'

export const api = {
  // 租户配置
  getTenantConfigs: () => axios.get(`${API_BASE}/config/tenant/`),
  createTenantConfig: (data) => axios.post(`${API_BASE}/config/tenant/`, data),
  updateTenantConfig: (id, data) => axios.put(`${API_BASE}/config/tenant/${id}/`, data),

  // 路由
  getRoutes: () => axios.get(`${API_BASE}/routes/`),
  createRoute: (data) => axios.post(`${API_BASE}/routes/`, data),
  updateRoute: (id, data) => axios.put(`${API_BASE}/routes/${id}/`, data),

  // SSL
  getSSLCerts: () => axios.get(`${API_BASE}/ssl/`),
  uploadSSLCert: (data) => axios.post(`${API_BASE}/ssl/`, data),

  // 防御策略
  applyDefensePolicy: (routeId, config) =>
    axios.post(`${API_BASE}/defense-plugin/apply_to_route/`, {
      route_id: routeId,
      defense_config: config
    }),

  // 监控
  getSyncStatus: () => axios.get(`${API_BASE}/sync-status/`),
  getMonitoring: () => axios.get(`${API_BASE}/monitor/global-sync/`),
}
```

```vue
<!-- TenantList.vue -->
<template>
  <div>
    <h2>租户配置</h2>
    <table>
      <tr>
        <th>租户 ID</th>
        <th>速率限制</th>
        <th>威胁阈值</th>
        <th>操作</th>
      </tr>
      <tr v-for="config in configs" :key="config.id">
        <td>{{ config.tenant }}</td>
        <td>{{ config.rate_limit }}</td>
        <td>{{ config.threat_threshold }}</td>
        <td>
          <button @click="editConfig(config)">编辑</button>
          <button @click="deleteConfig(config.id)">删除</button>
        </td>
      </tr>
    </table>
  </div>
</template>

<script>
import { api } from '@/api'

export default {
  data() {
    return {
      configs: []
    }
  },
  mounted() {
    this.loadConfigs()
  },
  methods: {
    async loadConfigs() {
      const res = await api.getTenantConfigs()
      this.configs = res.data.results
    },
    async editConfig(config) {
      // 打开编辑表单
    },
    async deleteConfig(id) {
      await api.deleteTenantConfig(id)
      this.loadConfigs()
    }
  }
}
</script>
```

## 性能优化

### 1. 数据库缓存
```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/0',
    }
}

# 在视图中使用
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # 缓存 5 分钟
def get_configs(request):
    ...
```

### 2. 数据库查询优化
```python
# views.py
def get_routes(self, request):
    # 使用 select_related 和 prefetch_related 优化查询
    queryset = Route.objects.select_related('tenant').prefetch_related('defense_policy')
    return queryset
```

### 3. 异步任务
```python
# 使用 Celery 处理耗时操作
from celery import shared_task

@shared_task
def sync_to_etcd(route_id):
    # 异步同步到 etcd
    pass
```

## 部署

### 开发环境
```bash
python manage.py runserver 0.0.0.0:8000
```

### 生产环境
```bash
gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --timeout 60
```

### Docker 部署
```dockerfile
FROM python:3.11

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY backend .
RUN python manage.py migrate

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

## 常见问题

### Q: 如何添加新模型？

A: 
1. 在 `defense/models.py` 中定义模型
2. 运行 `python manage.py makemigrations`
3. 运行 `python manage.py migrate`
4. 在 `defense/admin.py` 中注册

### Q: 如何自定义 API？

A:
1. 在 `defense/views.py` 中创建 ViewSet
2. 在 `config/urls.py` 中注册
3. 自动生成 API 和文档

### Q: 如何认证 API？

A:
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ]
}

# 使用 Token 认证
curl -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbea6d54e7" http://localhost:8000/api/v1/routes/
```

## 总结

Django 提供：
- ✅ 完整的 ORM 和数据库管理
- ✅ 自动生成的 Admin 后台
- ✅ 完整的 REST API 框架
- ✅ 信号系统自动同步 etcd
- ✅ 缓存和异步任务支持
- ✅ 完善的安全和认证机制

现在前端可以通过简洁的 REST API 与后端通信，所有功能都通过 Django 自动暴露！
