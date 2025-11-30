"""
Serializers for CDN Defense System API
"""
from rest_framework import serializers
from .models import (
    Tenant, TenantConfig, Route, SSLCertificate,
    DefensePolicy, SyncLog
)


class TenantSerializer(serializers.ModelSerializer):
    """租户序列化器"""
    class Meta:
        model = Tenant
        fields = ['id', 'tenant_id', 'name', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TenantConfigSerializer(serializers.ModelSerializer):
    """租户配置序列化器"""
    class Meta:
        model = TenantConfig
        fields = [
            'id', 'tenant', 'rate_limit', 'threat_threshold',
            'enabled_defense', 'js_challenge', 'bot_detection',
            'config_data', 'version', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class RouteSerializer(serializers.ModelSerializer):
    """路由序列化器"""
    class Meta:
        model = Route
        fields = [
            'id', 'route_id', 'tenant', 'path', 'upstream',
            'methods', 'strip_path', 'enabled', 'plugins',
            'version', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class SSLCertificateSerializer(serializers.ModelSerializer):
    """SSL 证书序列化器"""
    class Meta:
        model = SSLCertificate
        fields = [
            'id', 'cert_id', 'tenant', 'domain', 'cert', 'key',
            'expires_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'cert_id', 'created_at', 'updated_at']


class DefensePolicySerializer(serializers.ModelSerializer):
    """防御策略序列化器"""
    class Meta:
        model = DefensePolicy
        fields = [
            'id', 'route', 'enabled', 'threat_threshold',
            'challenge_type', 'js_fingerprint', 'rate_limit',
            'block_suspicious', 'config_data', 'version',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'version', 'created_at', 'updated_at']


class SyncLogSerializer(serializers.ModelSerializer):
    """同步日志序列化器"""
    class Meta:
        model = SyncLog
        fields = [
            'id', 'node_id', 'sync_type', 'resource_id',
            'status', 'version', 'details', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
