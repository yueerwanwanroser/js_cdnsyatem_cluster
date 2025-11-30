/**
 * CDN 防御系统 - 前端 API 客户端
 * 封装所有后端 API 调用
 */

import axios from 'axios'

const API_BASE_URL = process.env.VUE_APP_API_URL || 'http://localhost:5002/api'

// 创建 axios 实例
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器 - 添加租户 ID
api.interceptors.request.use((config) => {
  const tenantId = localStorage.getItem('tenantId') || 'default-tenant'
  config.headers['X-Tenant-ID'] = tenantId
  return config
}, (error) => {
  return Promise.reject(error)
})

// 响应拦截器 - 处理错误
api.interceptors.response.use((response) => {
  return response.data
}, (error) => {
  console.error('API 错误:', error)
  return Promise.reject(error.response?.data || error)
})

// ============ 配置 API ============

export const configAPI = {
  // 获取当前配置
  getConfig: () => api.get('/config'),

  // 更新配置
  updateConfig: (config) => api.post('/config', { config }),

  // 获取所有配置
  getAllConfigs: () => api.get('/config/all')
}

// ============ 路由 API ============

export const routesAPI = {
  // 获取路由列表
  list: () => api.get('/routes'),

  // 创建路由
  create: (route) => api.post('/routes', { route }),

  // 获取路由详情
  get: (routeId) => api.get(`/routes/${routeId}`),

  // 更新路由
  update: (routeId, updates) => api.put(`/routes/${routeId}`, { updates }),

  // 删除路由
  delete: (routeId) => api.delete(`/routes/${routeId}`)
}

// ============ SSL 证书 API ============

export const sslAPI = {
  // 获取证书列表
  list: () => api.get('/ssl'),

  // 上传证书
  upload: (cert) => api.post('/ssl', cert),

  // 删除证书
  delete: (certId) => api.delete(`/ssl/${certId}`)
}

// ============ 防御 API ============

export const defenseAPI = {
  // 为路由启用防御
  enable: (routeId, defenseConfig) =>
    api.post('/defense/enable', { route_id: routeId, defense_config: defenseConfig }),

  // 批量更新防御配置
  updateAll: (defenseConfig) => api.post('/defense/update-all', { defense_config: defenseConfig }),

  // 分析请求
  analyze: (request) => api.post('/analyze', { request }),

  // 获取统计信息
  getStatistics: () => api.get('/statistics'),

  // 获取日志
  getLogs: (params) => api.get('/logs', { params })
}

// ============ 监控 API ============

export const monitorAPI = {
  // 获取同步状态
  getSyncStatus: () => api.get('/sync/status'),

  // 刷新同步
  refreshSync: () => api.post('/sync/refresh'),

  // 获取全局监控信息
  getMonitorInfo: () => api.get('/monitor'),

  // 获取系统健康状态
  getHealth: () => api.get('/health'),

  // 获取服务信息
  getInfo: () => api.get('/info')
}

// ============ 工具函数 ============

/**
 * 设置租户 ID
 */
export const setTenantId = (tenantId) => {
  localStorage.setItem('tenantId', tenantId)
}

/**
 * 获取租户 ID
 */
export const getTenantId = () => {
  return localStorage.getItem('tenantId') || 'default-tenant'
}

/**
 * 格式化日期
 */
export const formatDate = (date) => {
  return new Date(date).toLocaleString('zh-CN')
}

/**
 * 显示通知
 */
export const notify = (message, type = 'info') => {
  // 这里可以集成 Element UI 的 ElNotification
  console.log(`[${type}] ${message}`)
}

export default api
