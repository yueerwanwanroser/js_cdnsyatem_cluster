"""
Signals for CDN Defense System
自动同步到 etcd 当 Django 模型改变时
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
import logging

from .models import TenantConfig, Route, SSLCertificate, DefensePolicy
from .services import GlobalConfigManager

logger = logging.getLogger(__name__)

config_manager = GlobalConfigManager()


@receiver(post_save, sender=TenantConfig)
def sync_tenant_config(sender, instance, created, **kwargs):
    """租户配置变更后同步到 etcd"""
    try:
        config_data = {
            'rate_limit': instance.rate_limit,
            'threat_threshold': instance.threat_threshold,
            'enabled_defense': instance.enabled_defense,
            'js_challenge': instance.js_challenge,
            'bot_detection': instance.bot_detection,
            'version': instance.version,
        }
        config_manager.set_tenant_config(
            instance.tenant.tenant_id,
            config_data
        )
        logger.info(f'Synced config for tenant {instance.tenant.tenant_id}')
    except Exception as e:
        logger.error(f'Failed to sync tenant config: {e}')


@receiver(post_save, sender=Route)
def sync_route(sender, instance, created, **kwargs):
    """路由变更后同步到 etcd"""
    try:
        route_data = {
            'id': instance.route_id,
            'path': instance.path,
            'upstream': instance.upstream,
            'methods': instance.methods,
            'strip_path': instance.strip_path,
            'enabled': instance.enabled,
            'tenant_id': instance.tenant.tenant_id,
            'version': instance.version,
        }
        config_manager.set_route(instance.route_id, route_data)
        logger.info(f'Synced route {instance.route_id}')
    except Exception as e:
        logger.error(f'Failed to sync route: {e}')


@receiver(post_save, sender=SSLCertificate)
def sync_ssl_cert(sender, instance, created, **kwargs):
    """SSL 证书变更后同步到 etcd"""
    try:
        cert_data = {
            'domain': instance.domain,
            'expires_at': instance.expires_at.isoformat(),
            'tenant_id': instance.tenant.tenant_id,
        }
        config_manager.set_ssl_cert(instance.cert_id, cert_data)
        logger.info(f'Synced SSL cert {instance.cert_id}')
    except Exception as e:
        logger.error(f'Failed to sync SSL cert: {e}')


@receiver(post_save, sender=DefensePolicy)
def sync_defense_policy(sender, instance, created, **kwargs):
    """防御策略变更后同步到 etcd"""
    try:
        defense_data = {
            'enabled': instance.enabled,
            'threat_threshold': instance.threat_threshold,
            'challenge_type': instance.challenge_type,
            'js_fingerprint': instance.js_fingerprint,
            'rate_limit': instance.rate_limit,
            'version': instance.version,
        }
        config_manager.enable_defense_plugin(
            instance.route.route_id,
            defense_data
        )
        logger.info(f'Synced defense policy for route {instance.route.route_id}')
    except Exception as e:
        logger.error(f'Failed to sync defense policy: {e}')
