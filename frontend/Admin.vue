<!--
CDN 防御系统 - 前端管理面板
Vue 3 + Element UI
-->

<template>
  <div class="app">
    <!-- 顶部导航 -->
    <el-header class="header">
      <div class="header-left">
        <h1>🛡️ CDN 防御系统</h1>
      </div>
      <div class="header-right">
        <el-dropdown>
          <span class="el-dropdown-link">
            {{ tenantId }}<i class="el-icon-arrow-down el-icon--right"></i>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="showTenantDialog = true">切换租户</el-dropdown-item>
              <el-dropdown-item @click="handleLogout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <!-- 主容器 -->
    <el-container>
      <!-- 侧边栏 -->
      <el-aside width="200px" class="sidebar">
        <el-menu
          :default-active="activeMenu"
          class="el-menu-vertical-demo"
          @select="handleMenuSelect"
        >
          <el-menu-item index="dashboard">
            <i class="el-icon-data-analysis"></i>
            <span>仪表盘</span>
          </el-menu-item>
          <el-menu-item index="config">
            <i class="el-icon-setting"></i>
            <span>配置管理</span>
          </el-menu-item>
          <el-menu-item index="routes">
            <i class="el-icon-connection"></i>
            <span>路由管理</span>
          </el-menu-item>
          <el-menu-item index="ssl">
            <i class="el-icon-document-copy"></i>
            <span>SSL 证书</span>
          </el-menu-item>
          <el-menu-item index="defense">
            <i class="el-icon-shield"></i>
            <span>防御策略</span>
          </el-menu-item>
          <el-menu-item index="statistics">
            <i class="el-icon-pie-chart"></i>
            <span>统计分析</span>
          </el-menu-item>
          <el-menu-item index="sync">
            <i class="el-icon-refresh"></i>
            <span>同步监控</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 主内容区 -->
      <el-main class="main-content">
        <!-- 仪表盘 -->
        <div v-show="activeMenu === 'dashboard'" class="page">
          <h2>仪表盘</h2>
          <el-row :gutter="20">
            <el-col :xs="24" :sm="12" :md="6">
              <el-card>
                <template #header>
                  <div class="card-header">
                    <span>总请求数</span>
                  </div>
                </template>
                <div class="stat-value">{{ stats.total_requests }}</div>
                <div class="stat-label">24h</div>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :md="6">
              <el-card>
                <template #header>
                  <div class="card-header">
                    <span>被阻止</span>
                  </div>
                </template>
                <div class="stat-value">{{ stats.blocked_requests }}</div>
                <div class="stat-label">24h</div>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :md="6">
              <el-card>
                <template #header>
                  <div class="card-header">
                    <span>平均威胁分数</span>
                  </div>
                </template>
                <div class="stat-value">{{ stats.avg_threat_score }}</div>
                <div class="stat-label">0-100</div>
              </el-card>
            </el-col>
            <el-col :xs="24" :sm="12" :md="6">
              <el-card>
                <template #header>
                  <div class="card-header">
                    <span>系统状态</span>
                  </div>
                </template>
                <div class="stat-value">
                  <el-tag :type="systemHealth === 'healthy' ? 'success' : 'danger'">
                    {{ systemHealth }}
                  </el-tag>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>

        <!-- 配置管理 -->
        <div v-show="activeMenu === 'config'" class="page">
          <h2>配置管理</h2>
          <el-button type="primary" @click="showConfigDialog = true">编辑配置</el-button>
          
          <el-table :data="[currentConfig]" style="margin-top: 20px">
            <el-table-column prop="rate_limit" label="速率限制"></el-table-column>
            <el-table-column prop="threat_threshold" label="威胁阈值"></el-table-column>
            <el-table-column prop="enabled_defense" label="防御状态">
              <template #default="{ row }">
                <el-tag :type="row.enabled_defense ? 'success' : 'danger'">
                  {{ row.enabled_defense ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="updated_at" label="更新时间"></el-table-column>
          </el-table>

          <!-- 配置编辑对话框 -->
          <el-dialog v-model="showConfigDialog" title="编辑配置">
            <el-form :model="editConfig" label-width="120px">
              <el-form-item label="速率限制">
                <el-input-number v-model="editConfig.rate_limit" :min="100" :max="100000"></el-input-number>
              </el-form-item>
              <el-form-item label="威胁阈值">
                <el-slider v-model="editConfig.threat_threshold" :min="0" :max="100"></el-slider>
              </el-form-item>
              <el-form-item label="启用防御">
                <el-switch v-model="editConfig.enabled_defense"></el-switch>
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="showConfigDialog = false">取消</el-button>
              <el-button type="primary" @click="saveConfig">保存</el-button>
            </template>
          </el-dialog>
        </div>

        <!-- 路由管理 -->
        <div v-show="activeMenu === 'routes'" class="page">
          <h2>路由管理</h2>
          <el-button type="primary" @click="showRouteDialog = true">添加路由</el-button>

          <el-table :data="routes" style="margin-top: 20px">
            <el-table-column prop="id" label="路由 ID"></el-table-column>
            <el-table-column prop="path" label="路径"></el-table-column>
            <el-table-column prop="upstream" label="上游地址"></el-table-column>
            <el-table-column label="操作" width="200">
              <template #default="{ row }">
                <el-button type="primary" size="small" @click="editRoute(row)">编辑</el-button>
                <el-button type="danger" size="small" @click="deleteRoute(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- 路由编辑对话框 -->
          <el-dialog v-model="showRouteDialog" :title="editingRoute ? '编辑路由' : '添加路由'">
            <el-form :model="editingRoute || {}" label-width="120px">
              <el-form-item label="路由 ID">
                <el-input v-model="(editingRoute || {}).id" :disabled="!!editingRoute"></el-input>
              </el-form-item>
              <el-form-item label="路径">
                <el-input v-model="(editingRoute || {}).path"></el-input>
              </el-form-item>
              <el-form-item label="上游地址">
                <el-input v-model="(editingRoute || {}).upstream"></el-input>
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="showRouteDialog = false">取消</el-button>
              <el-button type="primary" @click="saveRoute">保存</el-button>
            </template>
          </el-dialog>
        </div>

        <!-- SSL 证书 -->
        <div v-show="activeMenu === 'ssl'" class="page">
          <h2>SSL 证书管理</h2>
          <el-button type="primary" @click="showSSLDialog = true">上传证书</el-button>

          <el-table :data="sslCerts" style="margin-top: 20px">
            <el-table-column prop="domain" label="域名"></el-table-column>
            <el-table-column prop="expires_at" label="过期时间"></el-table-column>
            <el-table-column label="状态">
              <template #default="{ row }">
                <el-tag :type="isExpired(row.expires_at) ? 'danger' : 'success'">
                  {{ isExpired(row.expires_at) ? '已过期' : '有效' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作">
              <template #default="{ row }">
                <el-button type="danger" size="small">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <!-- SSL 上传对话框 -->
          <el-dialog v-model="showSSLDialog" title="上传 SSL 证书">
            <el-form :model="sslForm" label-width="120px">
              <el-form-item label="域名">
                <el-input v-model="sslForm.domain"></el-input>
              </el-form-item>
              <el-form-item label="证书">
                <el-input type="textarea" v-model="sslForm.cert" rows="4"></el-input>
              </el-form-item>
              <el-form-item label="私钥">
                <el-input type="textarea" v-model="sslForm.key" rows="4"></el-input>
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="showSSLDialog = false">取消</el-button>
              <el-button type="primary" @click="uploadSSL">上传</el-button>
            </template>
          </el-dialog>
        </div>

        <!-- 防御策略 -->
        <div v-show="activeMenu === 'defense'" class="page">
          <h2>防御策略</h2>
          <el-alert
            title="提示"
            type="info"
            description="为路由启用防御插件，所有请求将经过防御检查"
            :closable="false"
            style="margin-bottom: 20px"
          />
          
          <el-form :model="defenseForm" label-width="120px">
            <el-form-item label="路由">
              <el-select v-model="defenseForm.route_id" placeholder="选择路由">
                <el-option v-for="route in routes" :key="route.id" :label="route.id" :value="route.id"></el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="威胁阈值">
              <el-slider v-model="defenseForm.threat_threshold" :min="0" :max="100"></el-slider>
            </el-form-item>
            <el-form-item label="挑战类型">
              <el-select v-model="defenseForm.challenge_type">
                <el-option label="JavaScript" value="js"></el-option>
                <el-option label="滑块" value="slider"></el-option>
                <el-option label="验证码" value="captcha"></el-option>
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="applyDefense">应用防御</el-button>
            </el-form-item>
          </el-form>
        </div>

        <!-- 统计分析 -->
        <div v-show="activeMenu === 'statistics'" class="page">
          <h2>统计分析</h2>
          <el-row :gutter="20">
            <el-col :span="24">
              <el-card>
                <template #header>
                  <div class="card-header">
                    <span>请求统计</span>
                  </div>
                </template>
                <!-- 这里可以集成图表库如 ECharts -->
                <div style="height: 300px;">
                  <p>图表加载中...</p>
                </div>
              </el-card>
            </el-col>
          </el-row>
        </div>

        <!-- 同步监控 -->
        <div v-show="activeMenu === 'sync'" class="page">
          <h2>同步监控</h2>
          <el-button @click="refreshSync" :loading="syncLoading">刷新</el-button>

          <el-card style="margin-top: 20px">
            <template #header>
              <div class="card-header">
                <span>节点同步状态</span>
              </div>
            </template>
            <el-table :data="[syncStatus]">
              <el-table-column prop="node_id" label="节点ID"></el-table-column>
              <el-table-column prop="etcd_connected" label="etcd 连接">
                <template #default="{ row }">
                  <el-tag :type="row.etcd_connected ? 'success' : 'danger'">
                    {{ row.etcd_connected ? '已连接' : '断开' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="last_sync" label="最后同步时间"></el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-main>
    </el-container>

    <!-- 租户切换对话框 -->
    <el-dialog v-model="showTenantDialog" title="切换租户">
      <el-form :model="tenantForm" label-width="80px">
        <el-form-item label="租户 ID">
          <el-input v-model="tenantForm.tenantId"></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTenantDialog = false">取消</el-button>
        <el-button type="primary" @click="switchTenant">切换</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'

// 状态变量
const tenantId = ref('default-tenant')
const activeMenu = ref('dashboard')

const stats = reactive({
  total_requests: 5234,
  blocked_requests: 125,
  avg_threat_score: 35
})

const systemHealth = ref('healthy')
const currentConfig = reactive({
  rate_limit: 1000,
  threat_threshold: 70,
  enabled_defense: true,
  updated_at: new Date().toISOString()
})

const routes = ref([
  { id: 'api-1', path: '/api/v1/*', upstream: 'http://backend:8080' },
  { id: 'api-2', path: '/api/v2/*', upstream: 'http://backend:8081' }
])

const sslCerts = ref([
  { domain: 'api.example.com', expires_at: '2025-12-31' },
  { domain: 'cdn.example.com', expires_at: '2025-11-30' }
])

const syncStatus = reactive({
  node_id: 'node-1',
  etcd_connected: true,
  last_sync: new Date().toISOString()
})

// 对话框状态
const showConfigDialog = ref(false)
const showRouteDialog = ref(false)
const showSSLDialog = ref(false)
const showTenantDialog = ref(false)
const syncLoading = ref(false)

// 编辑表单
const editConfig = reactive({ ...currentConfig })
const editingRoute = ref(null)
const sslForm = reactive({ domain: '', cert: '', key: '' })
const tenantForm = reactive({ tenantId: 'default-tenant' })

const defenseForm = reactive({
  route_id: '',
  threat_threshold: 75,
  challenge_type: 'js'
})

// 方法
const handleMenuSelect = (key) => {
  activeMenu.value = key
}

const saveConfig = async () => {
  try {
    ElMessage.success('配置已保存')
    Object.assign(currentConfig, editConfig)
    showConfigDialog.value = false
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const editRoute = (row) => {
  editingRoute.value = { ...row }
  showRouteDialog.value = true
}

const deleteRoute = async (routeId) => {
  try {
    ElMessage.success(`路由 ${routeId} 已删除`)
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const saveRoute = async () => {
  try {
    ElMessage.success('路由已保存')
    showRouteDialog.value = false
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const uploadSSL = async () => {
  try {
    ElMessage.success('证书已上传')
    showSSLDialog.value = false
  } catch (error) {
    ElMessage.error('上传失败')
  }
}

const applyDefense = async () => {
  try {
    ElMessage.success('防御已应用')
  } catch (error) {
    ElMessage.error('应用失败')
  }
}

const refreshSync = async () => {
  syncLoading.value = true
  try {
    ElMessage.success('已刷新同步')
  } finally {
    syncLoading.value = false
  }
}

const switchTenant = () => {
  tenantId.value = tenantForm.tenantId
  ElMessage.success(`已切换到租户: ${tenantId.value}`)
  showTenantDialog.value = false
}

const handleLogout = () => {
  ElMessage.success('已退出登录')
}

const isExpired = (expiresAt) => {
  return new Date(expiresAt) < new Date()
}

onMounted(() => {
  // 初始化时加载数据
})
</script>

<style scoped>
.app {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background: linear-gradient(90deg, #1a1a2e, #16213e);
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.header h1 {
  margin: 0;
  font-size: 24px;
}

.el-container {
  flex: 1;
  overflow: hidden;
}

.sidebar {
  background: #f5f5f5;
  border-right: 1px solid #ddd;
  overflow-y: auto;
}

.main-content {
  overflow-y: auto;
  padding: 20px;
  background: #f9f9f9;
}

.page {
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.page h2 {
  margin-top: 0;
  color: #333;
  border-bottom: 2px solid #409eff;
  padding-bottom: 10px;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  color: #409eff;
}

.stat-label {
  color: #909399;
  font-size: 12px;
  margin-top: 5px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
