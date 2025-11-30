"""
ViewSets for CDN Defense System API
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
import logging

from .models import (
    Tenant, TenantConfig, Route, SSLCertificate,
    DefensePolicy, SyncLog
)
from .serializers import (
    TenantSerializer, TenantConfigSerializer, RouteSerializer,
    SSLCertificateSerializer, DefensePolicySerializer, SyncLogSerializer
)
from .services import GlobalConfigManager

logger = logging.getLogger(__name__)


class TenantConfigViewSet(viewsets.ModelViewSet):
    """
    租户配置 ViewSet
    - GET /api/v1/config/tenant/ - 列出所有配置
    - POST /api/v1/config/tenant/ - 创建配置
    - GET /api/v1/config/tenant/{id}/ - 获取配置
    - PUT /api/v1/config/tenant/{id}/ - 更新配置
    - DELETE /api/v1/config/tenant/{id}/ - 删除配置
    """
    queryset = TenantConfig.objects.all()
    serializer_class = TenantConfigSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['tenant', 'enabled_defense', 'js_challenge']

    def perform_create(self, serializer):
        """创建时同步到 etcd"""
        instance = serializer.save()
        # 同步到 etcd
        try:
            config_mgr = GlobalConfigManager()
            config_mgr.set_tenant_config(
                instance.tenant.tenant_id,
                {
                    'rate_limit': instance.rate_limit,
                    'threat_threshold': instance.threat_threshold,
                    'enabled_defense': instance.enabled_defense,
                    'js_challenge': instance.js_challenge,
                    'bot_detection': instance.bot_detection,
                }
            )
        except Exception as e:
            logger.error(f'Failed to sync to etcd: {e}')

    def perform_update(self, serializer):
        """更新时同步到 etcd"""
        instance = serializer.save()
        instance.version += 1
        instance.save()
        # 同步到 etcd
        try:
            config_mgr = GlobalConfigManager()
            config_mgr.set_tenant_config(
                instance.tenant.tenant_id,
                {
                    'rate_limit': instance.rate_limit,
                    'threat_threshold': instance.threat_threshold,
                    'enabled_defense': instance.enabled_defense,
                    'js_challenge': instance.js_challenge,
                    'bot_detection': instance.bot_detection,
                }
            )
        except Exception as e:
            logger.error(f'Failed to sync to etcd: {e}')


class RouteViewSet(viewsets.ModelViewSet):
    """
    路由 ViewSet
    - GET /api/v1/routes/ - 列出所有路由
    - POST /api/v1/routes/ - 创建路由
    - GET /api/v1/routes/{id}/ - 获取路由
    - PUT /api/v1/routes/{id}/ - 更新路由
    - DELETE /api/v1/routes/{id}/ - 删除路由
    """
    queryset = Route.objects.all()
    serializer_class = RouteSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['tenant', 'enabled', 'route_id']

    def perform_create(self, serializer):
        """创建时同步到 etcd"""
        instance = serializer.save()
        try:
            config_mgr = GlobalConfigManager()
            config_mgr.set_route(instance.route_id, {
                'id': instance.route_id,
                'path': instance.path,
                'upstream': instance.upstream,
                'methods': instance.methods,
                'strip_path': instance.strip_path,
                'enabled': instance.enabled,
                'tenant_id': instance.tenant.tenant_id,
            })
        except Exception as e:
            logger.error(f'Failed to sync route to etcd: {e}')

    def perform_update(self, serializer):
        """更新时同步到 etcd"""
        instance = serializer.save()
        instance.version += 1
        instance.save()
        try:
            config_mgr = GlobalConfigManager()
            config_mgr.set_route(instance.route_id, {
                'id': instance.route_id,
                'path': instance.path,
                'upstream': instance.upstream,
                'methods': instance.methods,
                'strip_path': instance.strip_path,
                'enabled': instance.enabled,
                'tenant_id': instance.tenant.tenant_id,
            })
        except Exception as e:
            logger.error(f'Failed to sync route to etcd: {e}')


class SSLCertificateViewSet(viewsets.ModelViewSet):
    """SSL 证书 ViewSet"""
    queryset = SSLCertificate.objects.all()
    serializer_class = SSLCertificateSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['tenant', 'domain']

    def perform_create(self, serializer):
        """创建时同步到 etcd"""
        instance = serializer.save()
        try:
            config_mgr = GlobalConfigManager()
            config_mgr.set_ssl_cert(instance.cert_id, {
                'domain': instance.domain,
                'cert': instance.cert,
                'key': instance.key,
                'expires_at': instance.expires_at.isoformat(),
            })
        except Exception as e:
            logger.error(f'Failed to sync SSL cert to etcd: {e}')


class DefensePluginViewSet(viewsets.ModelViewSet):
    """防御策略 ViewSet"""
    queryset = DefensePolicy.objects.all()
    serializer_class = DefensePolicySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['route', 'enabled', 'challenge_type']

    @action(detail=False, methods=['post'])
    def apply_to_route(self, request):
        """为路由应用防御策略"""
        route_id = request.data.get('route_id')
        defense_config = request.data.get('defense_config', {})

        try:
            route = Route.objects.get(route_id=route_id)
            policy, created = DefensePolicy.objects.update_or_create(
                route=route,
                defaults={
                    'enabled': defense_config.get('enabled', True),
                    'threat_threshold': defense_config.get('threat_threshold', 75),
                    'challenge_type': defense_config.get('challenge_type', 'js'),
                    'js_fingerprint': defense_config.get('js_fingerprint', True),
                    'rate_limit': defense_config.get('rate_limit', 1000),
                    'config_data': defense_config,
                }
            )

            # 同步到 etcd
            config_mgr = GlobalConfigManager()
            config_mgr.enable_defense_plugin(route_id, defense_config)

            return Response({
                'message': f'Defense policy applied to route {route_id}',
                'created': created,
                'policy': DefensePolicySerializer(policy).data
            })
        except Route.DoesNotExist:
            return Response(
                {'error': f'Route {route_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class SyncStatusView(APIView):
    """同步状态查询视图"""

    def get(self, request):
        """获取当前节点的同步状态"""
        try:
            config_mgr = GlobalConfigManager()
            cache_status = config_mgr.get_cache_status()

            return Response({
                'node_id': 'django-node',
                'sync_status': cache_status,
                'etcd_connected': True,
                'database_connected': True,
            })
        except Exception as e:
            logger.error(f'Error getting sync status: {e}')
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MonitoringView(APIView):
    """全局监控视图"""

    def get(self, request):
        """获取全局监控信息"""
        tenants = Tenant.objects.count()
        routes = Route.objects.count()
        ssl_certs = SSLCertificate.objects.count()
        policies = DefensePolicy.objects.count()

        return Response({
            'etcd_status': {
                'total_tenants': tenants,
                'total_routes': routes,
                'total_ssl_certs': ssl_certs,
                'total_defense_policies': policies,
            },
            'database_status': {
                'connected': True,
                'models': {
                    'tenants': tenants,
                    'routes': routes,
                    'ssl_certificates': ssl_certs,
                    'defense_policies': policies,
                }
            },
            'timestamp': None,
        })
