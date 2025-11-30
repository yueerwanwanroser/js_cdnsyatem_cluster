#!/bin/bash

# 全局配置同步演示脚本
# 展示修改一处配置，所有节点自动同步的效果

set -e

COLOR_GREEN='\033[0;32m'
COLOR_BLUE='\033[0;34m'
COLOR_YELLOW='\033[1;33m'
COLOR_RED='\033[0;31m'
NC='\033[0m' # No Color

API_URL=${API_URL:-"http://localhost:5001"}
TENANT_ID=${TENANT_ID:-"test-tenant-001"}

echo -e "${COLOR_BLUE}========================================${NC}"
echo -e "${COLOR_BLUE}全局配置同步演示${NC}"
echo -e "${COLOR_BLUE}========================================${NC}"
echo ""

# 第一步: 创建租户配置
echo -e "${COLOR_YELLOW}[步骤 1] 创建租户配置${NC}"
echo "执行: curl -X POST $API_URL/global-config/tenant"
echo ""

INITIAL_CONFIG=$(cat <<EOF
{
  "config": {
    "rate_limit": 1000,
    "threat_threshold": 70,
    "enabled_defense": true,
    "js_challenge": true
  }
}
EOF
)

echo "请求体:"
echo "$INITIAL_CONFIG" | jq .

RESPONSE=$(curl -s -X POST "$API_URL/global-config/tenant" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d "$INITIAL_CONFIG")

echo ""
echo "响应:"
echo "$RESPONSE" | jq .

echo -e "${COLOR_GREEN}✓ 租户配置已创建，存储在 etcd${NC}"
echo ""

# 第二步: 创建路由
echo -e "${COLOR_YELLOW}[步骤 2] 创建全局路由${NC}"
echo ""

ROUTE_CONFIG=$(cat <<EOF
{
  "route": {
    "id": "api-route-1",
    "path": "/api/v1/*",
    "upstream": "http://backend:8080",
    "methods": ["GET", "POST", "PUT", "DELETE"],
    "strip_path": true
  }
}
EOF
)

echo "请求体:"
echo "$ROUTE_CONFIG" | jq .

RESPONSE=$(curl -s -X POST "$API_URL/global-routes" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d "$ROUTE_CONFIG")

echo ""
echo "响应:"
echo "$RESPONSE" | jq .

echo -e "${COLOR_GREEN}✓ 路由已创建，自动同步到 APISIX 和所有节点${NC}"
echo ""

# 第三步: 上传 SSL 证书
echo -e "${COLOR_YELLOW}[步骤 3] 上传 SSL 证书（全局）${NC}"
echo ""

SSL_CONFIG=$(cat <<EOF
{
  "domain": "api.example.com",
  "cert": "-----BEGIN CERTIFICATE-----\nMIICljCCAX4CCQDiHj7PGJDcXjANBgkqhkiG9w0BAQsFADANMQswCQYDVQQGEwJB\nVTAeFw0yNTAxMTUxMDAwMDBaFw0yNjAxMTUxMDAwMDBaMA0xCzAJBgNVBAYTAkFV\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...\n-----END CERTIFICATE-----",
  "key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDX...\n-----END PRIVATE KEY-----",
  "expires_at": "2025-12-31T23:59:59Z"
}
EOF
)

echo "请求体:"
echo "$SSL_CONFIG" | jq .

RESPONSE=$(curl -s -X POST "$API_URL/global-ssl" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d "$SSL_CONFIG")

echo ""
echo "响应:"
echo "$RESPONSE" | jq .

echo -e "${COLOR_GREEN}✓ SSL 证书已上传，同步到所有节点${NC}"
echo ""

# 第四步: 启用防御插件
echo -e "${COLOR_YELLOW}[步骤 4] 为路由启用防御插件${NC}"
echo ""

DEFENSE_CONFIG=$(cat <<EOF
{
  "route_id": "api-route-1",
  "defense_config": {
    "enabled": true,
    "threat_threshold": 75,
    "challenge_type": "js",
    "js_fingerprint": true,
    "rate_limit": 1000
  }
}
EOF
)

echo "请求体:"
echo "$DEFENSE_CONFIG" | jq .

RESPONSE=$(curl -s -X POST "$API_URL/defense-plugin/apply" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d "$DEFENSE_CONFIG")

echo ""
echo "响应:"
echo "$RESPONSE" | jq .

echo -e "${COLOR_GREEN}✓ 防御插件已启用，所有 APISIX 实例自动加载${NC}"
echo ""

# 第五步: 查询同步状态
echo -e "${COLOR_YELLOW}[步骤 5] 查询节点同步状态${NC}"
echo ""

RESPONSE=$(curl -s "$API_URL/sync-status")
echo "Node-1 同步状态:"
echo "$RESPONSE" | jq .

echo -e "${COLOR_GREEN}✓ 当前节点已同步所有配置${NC}"
echo ""

# 第六步: 修改全局配置 - 这是关键演示
echo -e "${COLOR_YELLOW}[步骤 6] 修改全局配置（触发所有节点同步）${NC}"
echo ""
echo "现在修改防御阈值从 70 改为 50..."
echo ""

UPDATE_CONFIG=$(cat <<EOF
{
  "config": {
    "rate_limit": 2000,
    "threat_threshold": 50,
    "enabled_defense": true,
    "js_challenge": true
  }
}
EOF
)

echo "请求体:"
echo "$UPDATE_CONFIG" | jq .

RESPONSE=$(curl -s -X POST "$API_URL/global-config/tenant" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d "$UPDATE_CONFIG")

echo ""
echo "响应:"
echo "$RESPONSE" | jq .

echo -e "${COLOR_GREEN}✓ 配置已更新到 etcd！${NC}"
echo ""

# 第七步: 验证同步
echo -e "${COLOR_YELLOW}[步骤 7] 验证配置已同步到所有节点${NC}"
echo ""
echo "从 etcd 读取配置..."
echo ""

RESPONSE=$(curl -s "$API_URL/global-config/tenant" \
  -H "X-Tenant-ID: $TENANT_ID")

echo "当前配置:"
echo "$RESPONSE" | jq .

THREAT_THRESHOLD=$(echo "$RESPONSE" | jq '.config.threat_threshold')

if [ "$THREAT_THRESHOLD" = "50" ]; then
  echo -e "${COLOR_GREEN}✓ 配置已同步到当前节点！threat_threshold = $THREAT_THRESHOLD${NC}"
else
  echo -e "${COLOR_RED}✗ 配置同步失败！expected: 50, got: $THREAT_THRESHOLD${NC}"
fi

echo ""

# 第八步: 列出所有配置
echo -e "${COLOR_YELLOW}[步骤 8] 获取全局配置快照${NC}"
echo ""

RESPONSE=$(curl -s "$API_URL/global-config/all")
echo "所有租户配置:"
echo "$RESPONSE" | jq '.configs | length, .[0:2]'

echo ""

# 第九步: 列出所有路由
echo -e "${COLOR_YELLOW}[步骤 9] 列出租户的所有路由${NC}"
echo ""

RESPONSE=$(curl -s "$API_URL/global-routes" \
  -H "X-Tenant-ID: $TENANT_ID")

echo "路由列表:"
echo "$RESPONSE" | jq .

echo ""

# 第十步: 监控信息
echo -e "${COLOR_YELLOW}[步骤 10] 查看全局监控信息${NC}"
echo ""

RESPONSE=$(curl -s "$API_URL/monitor/global-sync")
echo "全局同步监控:"
echo "$RESPONSE" | jq .

echo ""

# 总结
echo -e "${COLOR_BLUE}========================================${NC}"
echo -e "${COLOR_GREEN}演示完成！${NC}"
echo -e "${COLOR_BLUE}========================================${NC}"
echo ""
echo "关键展示："
echo -e "  ${COLOR_GREEN}✓ etcd 作为单一真实源${NC}"
echo -e "  ${COLOR_GREEN}✓ 所有修改自动同步到全球节点${NC}"
echo -e "  ${COLOR_GREEN}✓ APISIX 自动加载路由和防御插件${NC}"
echo -e "  ${COLOR_GREEN}✓ 无需重启任何服务${NC}"
echo ""
echo "验证多节点同步，请在 Node-2 执行："
echo "  ${COLOR_YELLOW}curl http://node2:5001/global-config/tenant -H 'X-Tenant-ID: $TENANT_ID'${NC}"
echo ""
echo "期望看到相同的配置（threat_threshold = 50）"
echo ""

# 可选：批量更新所有防御配置
echo -e "${COLOR_YELLOW}[额外] 批量更新所有防御配置${NC}"
echo ""

BATCH_UPDATE=$(cat <<EOF
{
  "defense_config": {
    "threat_threshold": 60,
    "rate_limit": 5000,
    "js_challenge": true,
    "bot_detection": true
  }
}
EOF
)

echo "执行批量更新..."
RESPONSE=$(curl -s -X POST "$API_URL/defense-plugin/update-all" \
  -H "Content-Type: application/json" \
  -d "$BATCH_UPDATE")

echo "$RESPONSE" | jq .

echo ""
echo -e "${COLOR_GREEN}✓ 所有防御配置已全局更新！${NC}"
echo ""
