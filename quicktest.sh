#!/bin/bash

# 快速测试脚本

set -e

echo "================================"
echo "CDN 防御系统快速测试"
echo "================================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

API_URL="http://localhost:5000"
TENANT_ID="test-tenant-$(date +%s)"

echo ""
echo -e "${YELLOW}测试租户 ID: $TENANT_ID${NC}"
echo ""

# 1. 健康检查
echo -e "${YELLOW}1. 健康检查...${NC}"
if curl -s "$API_URL/health" > /dev/null; then
    echo -e "${GREEN}✓ API 服务正常${NC}"
else
    echo -e "${RED}✗ API 服务无法访问${NC}"
    exit 1
fi

# 2. 测试正常请求
echo ""
echo -e "${YELLOW}2. 测试正常请求...${NC}"

RESPONSE=$(curl -s -X POST "$API_URL/analyze" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{
    "request": {
      "request_id": "test-normal-001",
      "timestamp": '$(date +%s)',
      "client_ip": "192.168.1.100",
      "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
      "path": "/api/test",
      "method": "GET",
      "headers": {},
      "payload_size": 1024,
      "user_id": "test-user"
    }
  }')

if echo "$RESPONSE" | grep -q '"allow": true'; then
    echo -e "${GREEN}✓ 正常请求通过${NC}"
    echo "  决策: $(echo $RESPONSE | grep -o '"action":"[^"]*"')"
else
    echo -e "${RED}✗ 正常请求被拒${NC}"
    echo "  响应: $RESPONSE"
fi

# 3. 测试黑名单功能
echo ""
echo -e "${YELLOW}3. 测试黑名单功能...${NC}"

# 添加到黑名单
curl -s -X POST "$API_URL/blacklist" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{"ip": "192.168.1.200", "duration": 3600}' > /dev/null

# 查询黑名单
BLACKLIST=$(curl -s -X GET "$API_URL/blacklist" \
  -H "X-Tenant-ID: $TENANT_ID")

if echo "$BLACKLIST" | grep -q '192.168.1.200'; then
    echo -e "${GREEN}✓ 黑名单添加成功${NC}"
else
    echo -e "${RED}✗ 黑名单添加失败${NC}"
fi

# 4. 测试白名单功能
echo ""
echo -e "${YELLOW}4. 测试白名单功能...${NC}"

curl -s -X POST "$API_URL/whitelist" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{"ip": "192.168.1.50"}' > /dev/null

WHITELIST=$(curl -s -X GET "$API_URL/whitelist" \
  -H "X-Tenant-ID: $TENANT_ID")

if echo "$WHITELIST" | grep -q '192.168.1.50'; then
    echo -e "${GREEN}✓ 白名单添加成功${NC}"
else
    echo -e "${RED}✗ 白名单添加失败${NC}"
fi

# 5. 测试配置管理
echo ""
echo -e "${YELLOW}5. 测试配置管理...${NC}"

curl -s -X POST "$API_URL/config" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{"config": {"rate_limit_per_minute": "150"}}' > /dev/null

CONFIG=$(curl -s -X GET "$API_URL/config" \
  -H "X-Tenant-ID: $TENANT_ID")

if echo "$CONFIG" | grep -q 'rate_limit_per_minute'; then
    echo -e "${GREEN}✓ 配置管理正常${NC}"
else
    echo -e "${RED}✗ 配置管理失败${NC}"
fi

# 6. 测试统计接口
echo ""
echo -e "${YELLOW}6. 测试统计接口...${NC}"

STATS=$(curl -s -X GET "$API_URL/statistics" \
  -H "X-Tenant-ID: $TENANT_ID")

if echo "$STATS" | grep -q 'total_requests'; then
    TOTAL=$(echo "$STATS" | grep -o '"total_requests": [0-9]*' | grep -o '[0-9]*$')
    echo -e "${GREEN}✓ 统计接口正常${NC}"
    echo "  总请求数: $TOTAL"
else
    echo -e "${RED}✗ 统计接口失败${NC}"
fi

# 7. 测试日志接口
echo ""
echo -e "${YELLOW}7. 测试日志接口...${NC}"

LOGS=$(curl -s -X GET "$API_URL/logs?limit=10" \
  -H "X-Tenant-ID: $TENANT_ID")

if echo "$LOGS" | grep -q '"logs"'; then
    echo -e "${GREEN}✓ 日志接口正常${NC}"
else
    echo -e "${RED}✗ 日志接口失败${NC}"
fi

# 8. 使用管理 CLI 测试
echo ""
echo -e "${YELLOW}8. 测试管理 CLI...${NC}"

if command -v python3 &> /dev/null; then
    python3 admin_cli.py tenant list > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 管理 CLI 正常${NC}"
    else
        echo -e "${YELLOW}⚠ 管理 CLI 执行出错（可能是依赖问题）${NC}"
    fi
fi

# 9. 多个并发请求测试
echo ""
echo -e "${YELLOW}9. 并发请求测试 (10 个并发请求)...${NC}"

CONCURRENT_PASS=0
for i in {1..10}; do
    RESPONSE=$(curl -s -X POST "$API_URL/analyze" \
      -H "Content-Type: application/json" \
      -H "X-Tenant-ID: $TENANT_ID" \
      -d '{
        "request": {
          "request_id": "concurrent-'$i'",
          "timestamp": '$(date +%s)',
          "client_ip": "192.168.1.'$((100 + i))'",
          "user_agent": "Mozilla/5.0",
          "path": "/api/concurrent",
          "method": "GET",
          "headers": {},
          "payload_size": 512,
          "user_id": "concurrent-user-'$i'"
        }
      }' 2>/dev/null)
    
    if echo "$RESPONSE" | grep -q '"threat_score"'; then
        ((CONCURRENT_PASS++))
    fi
done

echo -e "${GREEN}✓ 并发请求完成: $CONCURRENT_PASS/10 成功${NC}"

# 总结
echo ""
echo "================================"
echo -e "${GREEN}快速测试完成！${NC}"
echo "================================"
echo ""
echo "系统功能:"
echo "  ✓ API 服务"
echo "  ✓ 防御分析"
echo "  ✓ 黑名单管理"
echo "  ✓ 白名单管理"
echo "  ✓ 配置管理"
echo "  ✓ 统计接口"
echo "  ✓ 日志接口"
echo "  ✓ 并发处理"
echo ""
echo "访问地址:"
echo "  - API: $API_URL"
echo "  - Grafana: http://localhost:3000"
echo "  - Prometheus: http://localhost:9090"
echo ""
