#!/bin/bash

# Django CDN Defense System 启动脚本

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║  Django CDN 防御系统启动                                   ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 设置环境
export DJANGO_SETTINGS_MODULE=config.settings
cd "$(dirname "$0")/backend"

echo -e "${BLUE}📦 安装依赖...${NC}"
pip install -q -r ../requirements.txt

echo -e "${BLUE}🗄️  初始化数据库...${NC}"
python manage.py migrate

echo -e "${BLUE}📝 创建超级用户...${NC}"
if ! python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('✓ 超级用户已创建 (admin/admin123)')
else:
    print('✓ 超级用户已存在')
EOF
then
    echo "✓ 跳过超级用户创建"
fi

echo ""
echo -e "${GREEN}✅ Django 系统已就绪！${NC}"
echo ""
echo -e "${YELLOW}启动命令:${NC}"
echo "  开发服务器: python manage.py runserver 0.0.0.0:8000"
echo "  生产服务器: gunicorn config.wsgi:application --bind 0.0.0.0:8000"
echo ""
echo -e "${YELLOW}后台访问:${NC}"
echo "  URL: http://localhost:8000/admin/"
echo "  用户名: admin"
echo "  密码: admin123"
echo ""
echo -e "${YELLOW}API 文档:${NC}"
echo "  URL: http://localhost:8000/api/docs/"
echo ""
echo -e "${YELLOW}API 端点:${NC}"
echo "  租户配置: http://localhost:8000/api/v1/config/tenant/"
echo "  路由管理: http://localhost:8000/api/v1/routes/"
echo "  SSL 证书: http://localhost:8000/api/v1/ssl/"
echo "  防御策略: http://localhost:8000/api/v1/defense-plugin/"
echo "  同步状态: http://localhost:8000/api/v1/sync-status/"
echo "  监控信息: http://localhost:8000/api/v1/monitor/global-sync/"
echo ""

# 启动开发服务器
echo -e "${BLUE}🚀 启动 Django 开发服务器...${NC}"
python manage.py runserver 0.0.0.0:8000
