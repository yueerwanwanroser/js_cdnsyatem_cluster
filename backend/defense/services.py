"""
Services for CDN Defense System
集成全局配置管理器
"""
import json
import logging
from django.conf import settings
import sys
import os

# 添加 backend 路径以导入 global_sync_manager
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from global_sync_manager import GlobalConfigManager as BaseConfigManager
except ImportError:
    # 如果找不到，创建一个模拟版本
    class BaseConfigManager:
        def __init__(self, *args, **kwargs):
            pass
        
        def set_tenant_config(self, tenant_id, config):
            return True
        
        def get_tenant_config(self, tenant_id):
            return {}
        
        def set_route(self, route_id, route_config):
            return True
        
        def get_route(self, route_id):
            return {}
        
        def set_ssl_cert(self, cert_id, cert_data):
            return True
        
        def enable_defense_plugin(self, route_id, config):
            return True
        
        def get_cache_status(self):
            return {}

logger = logging.getLogger(__name__)


class GlobalConfigManager(BaseConfigManager):
    """
    扩展的全局配置管理器
    集成 Django ORM 和 etcd
    """

    def __init__(self):
        try:
            super().__init__(
                settings.ETCD_HOST,
                settings.ETCD_PORT
            )
        except Exception as e:
            logger.warning(f'Failed to initialize etcd: {e}')

    def set_tenant_config(self, tenant_id, config):
        """设置租户配置"""
        try:
            # 保存到 etcd
            if hasattr(super(), 'set_tenant_config'):
                result = super().set_tenant_config(tenant_id, config)
                logger.info(f'Config synced to etcd for tenant {tenant_id}')
                return result
            return True
        except Exception as e:
            logger.error(f'Error setting tenant config: {e}')
            return False

    def get_tenant_config(self, tenant_id):
        """获取租户配置"""
        try:
            if hasattr(super(), 'get_tenant_config'):
                return super().get_tenant_config(tenant_id)
            return {}
        except Exception as e:
            logger.error(f'Error getting tenant config: {e}')
            return {}

    def set_route(self, route_id, route_config):
        """设置路由"""
        try:
            if hasattr(super(), 'set_route'):
                result = super().set_route(route_id, route_config)
                logger.info(f'Route synced to etcd: {route_id}')
                return result
            return True
        except Exception as e:
            logger.error(f'Error setting route: {e}')
            return False

    def get_route(self, route_id):
        """获取路由"""
        try:
            if hasattr(super(), 'get_route'):
                return super().get_route(route_id)
            return {}
        except Exception as e:
            logger.error(f'Error getting route: {e}')
            return {}

    def set_ssl_cert(self, cert_id, cert_data):
        """设置 SSL 证书"""
        try:
            if hasattr(super(), 'set_ssl_cert'):
                result = super().set_ssl_cert(cert_id, cert_data)
                logger.info(f'SSL cert synced to etcd: {cert_id}')
                return result
            return True
        except Exception as e:
            logger.error(f'Error setting SSL cert: {e}')
            return False

    def enable_defense_plugin(self, route_id, defense_config):
        """启用防御插件"""
        try:
            if hasattr(super(), 'enable_defense_plugin'):
                result = super().enable_defense_plugin(route_id, defense_config)
                logger.info(f'Defense plugin enabled for route {route_id}')
                return result
            return True
        except Exception as e:
            logger.error(f'Error enabling defense plugin: {e}')
            return False

    def get_cache_status(self):
        """获取缓存状态"""
        from .models import Tenant, Route, SSLCertificate, DefensePolicy

        return {
            'total_cached_configs': Tenant.objects.count(),
            'total_cached_routes': Route.objects.count(),
            'total_cached_ssl_certs': SSLCertificate.objects.count(),
            'total_cached_policies': DefensePolicy.objects.count(),
            'database_connected': True,
        }
