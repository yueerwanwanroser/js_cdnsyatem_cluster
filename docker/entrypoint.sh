#!/bin/bash

set -e

echo "====================================="
echo "  Django 数据库迁移和初始化"
echo "====================================="

# 等待数据库就绪
echo "等待数据库启动..."
while ! nc -z ${DB_HOST:-postgres} ${DB_PORT:-5432}; do
  sleep 1
done
echo "数据库已启动"

# 等待 etcd 就绪
echo "等待 etcd 启动..."
while ! nc -z ${ETCD_HOST:-etcd} ${ETCD_PORT:-2379}; do
  sleep 1
done
echo "etcd 已启动"

# 运行迁移
echo "运行数据库迁移..."
python manage.py migrate --noinput

# 创建超级用户 (如果不存在)
echo "检查超级用户..."
python manage.py shell <<EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print("✅ 创建超级用户: admin/admin123")
else:
    print("✅ 超级用户已存在")
EOF

# 收集静态文件
echo "收集静态文件..."
python manage.py collectstatic --noinput 2>/dev/null || true

echo "====================================="
echo "✅ 初始化完成！启动应用..."
echo "====================================="

# 启动应用
exec "$@"
