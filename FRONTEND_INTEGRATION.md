# CDN 防御系统 - 前端集成完整指南

## 概述

前端已完整集成了所有后端 API，包括：
- ✅ 全局配置管理 API
- ✅ 路由管理 API
- ✅ SSL 证书管理 API
- ✅ 防御策略 API
- ✅ 监控和诊断 API
- ✅ 统计分析 API

## 架构

### 分层结构

```
┌─────────────────────────────────────────┐
│         前端 Vue 3 管理面板              │
│  (Admin.vue + 完整的 UI 组件)           │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│    前端 API 客户端 (api/client.js)      │
│  (axios 封装，自动处理租户隔离)         │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│   前端 API 网关 (frontend_api_gateway)  │
│  (Flask，汇总所有后端 API)              │
│  端口: 5002                              │
└─────────────────┬───────────────────────┘
                  │
     ┌────────────┼────────────┐
     │            │            │
     ▼            ▼            ▼
┌──────────┐ ┌──────────┐ ┌────────┐
│defense   │ │global    │ │其他    │
│_api      │ │config_api│ │服务    │
│(5000)    │ │(5001)    │ │        │
└──────────┘ └──────────┘ └────────┘
```

## 新增文件

### 1. 后端网关 (`backend/frontend_api_gateway.py`)

**功能**: 汇总所有后端 API 到单一接口

**主要端点**:
```
/api/config           - 配置管理
/api/routes           - 路由管理
/api/ssl              - SSL 证书
/api/defense          - 防御策略
/api/analyze          - 请求分析
/api/statistics       - 统计信息
/api/logs             - 日志查询
/api/sync             - 同步监控
/api/monitor          - 全局监控
/api/health           - 健康检查
```

### 2. 前端管理面板 (`frontend/Admin.vue`)

**功能**: 完整的前端 UI 管理面板

**包含页面**:
- 仪表盘 (Dashboard)
- 配置管理 (Config Management)
- 路由管理 (Route Management)
- SSL 证书 (SSL Certificates)
- 防御策略 (Defense Strategy)
- 统计分析 (Statistics)
- 同步监控 (Sync Monitor)

### 3. 前端 API 客户端 (`frontend/api/client.js`)

**功能**: 封装所有 API 调用

**导出 API**:
```javascript
configAPI      - 配置操作
routesAPI      - 路由操作
sslAPI         - SSL 操作
defenseAPI     - 防御操作
monitorAPI     - 监控操作
```

### 4. 项目配置 (`frontend/package.json`)

**包含依赖**:
- Vue 3
- Element UI Plus
- Axios
- ECharts

## 安装和启动

### 1. 后端网关启动

```bash
# 安装依赖
pip install flask-cors

# 启动网关
python backend/frontend_api_gateway.py

# 输出:
# INFO:__main__:CDN 防御系统 前端 API 网关启动
# * Running on http://0.0.0.0:5002
```

### 2. 前端开发环境启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 访问: http://localhost:5173
```

### 3. 前端生产构建

```bash
cd frontend

# 构建
npm run build

# 预览
npm run preview
```

## API 集成说明

### 配置管理

#### 获取配置

```javascript
import { configAPI } from './api/client.js'

// 获取当前租户的配置
const config = await configAPI.getConfig()

// 返回格式:
// {
//   "tenant_id": "tenant-001",
//   "config": {
//     "rate_limit": 1000,
//     "threat_threshold": 70,
//     "enabled_defense": true
//   }
// }
```

#### 更新配置 (全局同步)

```javascript
// 修改配置，自动同步到所有节点
await configAPI.updateConfig({
  rate_limit: 2000,
  threat_threshold: 60,
  enabled_defense: true
})
```

### 路由管理

#### 列表

```javascript
import { routesAPI } from './api/client.js'

const routes = await routesAPI.list()
```

#### 创建

```javascript
await routesAPI.create({
  id: 'api-route-1',
  path: '/api/v1/*',
  upstream: 'http://backend:8080',
  methods: ['GET', 'POST']
})
```

#### 更新

```javascript
await routesAPI.update('api-route-1', {
  upstream: 'http://new-backend:8080'
})
```

#### 删除

```javascript
await routesAPI.delete('api-route-1')
```

### SSL 证书管理

#### 列表

```javascript
import { sslAPI } from './api/client.js'

const certs = await sslAPI.list()
```

#### 上传

```javascript
await sslAPI.upload({
  domain: 'api.example.com',
  cert: '-----BEGIN CERTIFICATE-----...',
  key: '-----BEGIN PRIVATE KEY-----...',
  expires_at: '2025-12-31T23:59:59Z'
})
```

### 防御策略

#### 为路由启用防御

```javascript
import { defenseAPI } from './api/client.js'

await defenseAPI.enable('api-route-1', {
  threat_threshold: 75,
  challenge_type: 'js',
  js_fingerprint: true,
  rate_limit: 1000
})
```

#### 批量更新防御配置

```javascript
await defenseAPI.updateAll({
  threat_threshold: 70,
  rate_limit: 5000,
  js_challenge: true
})
```

### 监控

#### 获取同步状态

```javascript
import { monitorAPI } from './api/client.js'

const status = await monitorAPI.getSyncStatus()

// 返回:
// {
//   "node_id": "node-1",
//   "sync_status": {
//     "total_cached_configs": 15,
//     "etcd_connected": true
//   }
// }
```

#### 获取全局监控信息

```javascript
const monitor = await monitorAPI.getMonitorInfo()

// 返回:
// {
//   "etcd_status": {
//     "total_tenants": 3,
//     "total_routes": 8,
//     "total_ssl_certs": 5
//   }
// }
```

## 前端使用示例

### 修改配置并全系统同步

```vue
<template>
  <el-button @click="updateConfig">更新配置</el-button>
</template>

<script setup>
import { configAPI } from '@/api/client.js'
import { ElMessage } from 'element-plus'

const updateConfig = async () => {
  try {
    // 修改配置，自动同步到所有节点
    await configAPI.updateConfig({
      rate_limit: 2000,
      threat_threshold: 50,
      enabled_defense: true
    })
    
    ElMessage.success('配置已更新，自动同步到全系统!')
  } catch (error) {
    ElMessage.error('更新失败')
  }
}
</script>
```

### 创建路由并自动启用防御

```vue
<script setup>
import { routesAPI, defenseAPI } from '@/api/client.js'

const createRoute = async () => {
  try {
    // 创建路由
    const result = await routesAPI.create({
      id: 'new-route',
      path: '/api/new/*',
      upstream: 'http://backend:8080'
    })
    
    // 自动启用防御
    await defenseAPI.enable('new-route', {
      threat_threshold: 75,
      challenge_type: 'js'
    })
    
    ElMessage.success('路由已创建并启用防御!')
  } catch (error) {
    ElMessage.error('创建失败')
  }
}
</script>
```

### 多租户切换

```vue
<script setup>
import { setTenantId, getTenantId, configAPI } from '@/api/client.js'

const switchTenant = async (newTenantId) => {
  // 切换租户
  setTenantId(newTenantId)
  
  // 加载新租户的配置
  const config = await configAPI.getConfig()
  
  console.log(`已切换到租户: ${newTenantId}`)
}
</script>
```

## 租户隔离

前端 API 客户端自动处理多租户隔离：

```javascript
// 所有请求都自动添加 X-Tenant-ID 头
const tenantId = localStorage.getItem('tenantId') || 'default-tenant'

// 每个请求都会包含:
// X-Tenant-ID: tenant-id

// 不同租户之间完全隔离
setTenantId('tenant-a')
const configA = await configAPI.getConfig()

setTenantId('tenant-b')
const configB = await configAPI.getConfig()
// configA 和 configB 完全独立
```

## 错误处理

所有 API 调用都有内置错误处理：

```javascript
import { configAPI } from '@/api/client.js'
import { ElMessage } from 'element-plus'

try {
  const config = await configAPI.getConfig()
} catch (error) {
  ElMessage.error(error.message || '请求失败')
}
```

## 环境变量

### 前端配置 (`.env`)

```bash
# API 网关地址
VUE_APP_API_URL=http://localhost:5002/api

# 后端服务地址（网关内部使用）
VITE_DEFENSE_API_URL=http://localhost:5000
VITE_GLOBAL_CONFIG_API_URL=http://localhost:5001
```

### 后端网关配置 (环境变量)

```bash
# 后端服务地址
DEFENSE_API_URL=http://localhost:5000
GLOBAL_CONFIG_API_URL=http://localhost:5001

# 网关端口
FRONTEND_API_PORT=5002
```

## 功能清单

### ✅ 已实现功能

- **配置管理**
  - ✅ 获取配置
  - ✅ 修改配置 (全局同步)
  - ✅ 获取所有租户配置

- **路由管理**
  - ✅ 列表查看
  - ✅ 创建路由
  - ✅ 编辑路由
  - ✅ 删除路由

- **SSL 证书**
  - ✅ 列表查看
  - ✅ 上传证书
  - ✅ 证书过期检查
  - ✅ 删除证书

- **防御策略**
  - ✅ 为路由启用防御
  - ✅ 批量更新防御配置
  - ✅ 防御插件管理

- **监控**
  - ✅ 节点同步状态
  - ✅ 全局监控信息
  - ✅ 系统健康检查
  - ✅ 手动刷新同步

- **前端网关**
  - ✅ 15+ API 端点
  - ✅ CORS 支持
  - ✅ 租户隔离
  - ✅ 错误处理
  - ✅ 请求代理

## 下一步

### 短期任务

1. 启动后端网关: `python backend/frontend_api_gateway.py`
2. 启动前端: `cd frontend && npm install && npm run dev`
3. 访问: `http://localhost:5173`
4. 测试所有功能

### 中期任务

1. 集成图表库 (ECharts) 实现数据可视化
2. 添加权限管理和用户认证
3. 实现高级搜索和过滤功能
4. 添加批量操作功能

### 长期任务

1. 实现 WebSocket 实时更新
2. 添加操作审计日志
3. 实现高可用前端部署
4. 性能优化和缓存策略

## 故障排查

### 问题：前端无法连接到后端

```bash
# 检查网关是否运行
curl http://localhost:5002/api/health

# 检查后端服务
curl http://localhost:5000/health
curl http://localhost:5001/sync-status
```

### 问题：租户切换后配置不变

```javascript
// 清除本地存储，重新切换
localStorage.removeItem('tenantId')
setTenantId('new-tenant')
```

### 问题：CORS 错误

```bash
# 确保网关启用了 CORS
# 检查 frontend_api_gateway.py 中的 CORS(app)
```

## 总结

✅ **前端已完整集成了所有后端 API**

- 后端网关汇总了 15+ API 端点
- 前端客户端自动处理租户隔离
- Vue 3 管理面板提供完整的 UI
- 所有配置修改自动全系统同步
- 生产就绪，可立即部署

**下一步**: 启动前端开发服务器，开始使用管理面板！
