from django.contrib import admin
from .models import (
    Tenant, TenantConfig, Route, SSLCertificate,
    DefensePolicy, SyncLog
)


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['tenant_id', 'name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['tenant_id', 'name']


@admin.register(TenantConfig)
class TenantConfigAdmin(admin.ModelAdmin):
    list_display = ['tenant', 'rate_limit', 'threat_threshold', 'version', 'updated_at']
    list_filter = ['enabled_defense', 'js_challenge', 'bot_detection']
    search_fields = ['tenant__tenant_id']
    readonly_fields = ['version', 'created_at', 'updated_at']


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ['route_id', 'tenant', 'path', 'enabled', 'version', 'created_at']
    list_filter = ['enabled', 'created_at']
    search_fields = ['route_id', 'path']
    readonly_fields = ['version', 'created_at', 'updated_at']


@admin.register(SSLCertificate)
class SSLCertificateAdmin(admin.ModelAdmin):
    list_display = ['cert_id', 'domain', 'tenant', 'expires_at', 'created_at']
    list_filter = ['expires_at', 'created_at']
    search_fields = ['cert_id', 'domain']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(DefensePolicy)
class DefensePolicyAdmin(admin.ModelAdmin):
    list_display = ['route', 'enabled', 'threat_threshold', 'challenge_type', 'version']
    list_filter = ['enabled', 'challenge_type']
    search_fields = ['route__route_id']
    readonly_fields = ['version', 'created_at', 'updated_at']


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = ['node_id', 'sync_type', 'resource_id', 'status', 'version', 'created_at']
    list_filter = ['sync_type', 'status', 'created_at']
    search_fields = ['node_id', 'resource_id']
    readonly_fields = ['created_at']
