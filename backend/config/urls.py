"""
URL configuration for CDN Defense System.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.static import serve
from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.documentation import include_docs_urls

# Import API viewsets
from defense.views import (
    TenantConfigViewSet,
    RouteViewSet,
    SSLCertificateViewSet,
    DefensePluginViewSet,
    SyncStatusView,
    MonitoringView,
)

# Import UI views
from defense.views_ui.dashboard import dashboard_view, dashboard_stats_api
from defense.views_ui.config import config_management_view, config_api, config_update_api
from defense.views_ui.routes import (
    route_management_view, routes_list_api, route_create_api,
    route_update_api, route_delete_api
)
from defense.views_ui.ssl import (
    ssl_management_view, ssl_list_api, ssl_upload_api, ssl_delete_api
)
from defense.views_ui.defense import (
    defense_strategy_view, defense_policies_api, defense_policy_create_api,
    defense_policy_update_api, defense_policy_delete_api
)
from defense.views_ui.statistics import (
    statistics_view, statistics_data_api, top_blocked_ips_api
)
from defense.views_ui.sync import (
    sync_monitoring_view, sync_status_api, sync_refresh_api
)
from defense.views_ui.auth import (
    login_view, logout_view, index_view, tenant_switch_api
)

# Create router for API endpoints
router = DefaultRouter()
router.register(r'config/tenant', TenantConfigViewSet, basename='tenant-config')
router.register(r'routes', RouteViewSet, basename='routes')
router.register(r'ssl', SSLCertificateViewSet, basename='ssl')
router.register(r'defense-plugin', DefensePluginViewSet, basename='defense-plugin')

urlpatterns = [
    # Home
    path('', index_view, name='index'),
    
    # Authentication
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/docs/', include_docs_urls(title='CDN Defense System API')),
    
    # REST API Endpoints
    path('api/v1/', include(router.urls)),
    path('api/v1/sync-status/', SyncStatusView.as_view(), name='sync-status'),
    path('api/v1/monitor/global-sync/', MonitoringView.as_view(), name='monitoring'),
    path('api/v1/tenant/switch/', tenant_switch_api, name='tenant-switch'),
    
    # Django UI Views - Dashboard
    path('defense/dashboard/', dashboard_view, name='dashboard'),
    path('defense/api/dashboard/stats/', dashboard_stats_api, name='dashboard-stats'),
    
    # Django UI Views - Configuration
    path('defense/config/', config_management_view, name='config_management'),
    path('defense/api/config/', config_api, name='config-api-get'),
    path('defense/api/config/update/', config_update_api, name='config-api-update'),
    
    # Django UI Views - Routes
    path('defense/routes/', route_management_view, name='route_management'),
    path('defense/api/routes/', routes_list_api, name='routes-list'),
    path('defense/api/routes/', route_create_api, name='routes-create'),
    path('defense/api/routes/<str:route_id>/', route_update_api, name='routes-update'),
    path('defense/api/routes/<str:route_id>/', route_delete_api, name='routes-delete'),
    
    # Django UI Views - SSL
    path('defense/ssl/', ssl_management_view, name='ssl_management'),
    path('defense/api/ssl/', ssl_list_api, name='ssl-list'),
    path('defense/api/ssl/', ssl_upload_api, name='ssl-upload'),
    path('defense/api/ssl/<str:cert_id>/', ssl_delete_api, name='ssl-delete'),
    
    # Django UI Views - Defense Strategy
    path('defense/defense/', defense_strategy_view, name='defense_strategy'),
    path('defense/api/defense-policies/', defense_policies_api, name='defense-policies-list'),
    path('defense/api/defense-policies/', defense_policy_create_api, name='defense-policies-create'),
    path('defense/api/defense-policies/<int:policy_id>/', defense_policy_update_api, name='defense-policies-update'),
    path('defense/api/defense-policies/<int:policy_id>/', defense_policy_delete_api, name='defense-policies-delete'),
    
    # Django UI Views - Statistics
    path('defense/statistics/', statistics_view, name='statistics'),
    path('defense/api/statistics/', statistics_data_api, name='statistics-data'),
    path('defense/api/statistics/top-blocked-ips/', top_blocked_ips_api, name='top-blocked-ips'),
    
    # Django UI Views - Sync Monitoring
    path('defense/sync/', sync_monitoring_view, name='sync_monitoring'),
    path('defense/api/sync-status/', sync_status_api, name='sync-status-api'),
    path('defense/api/sync-refresh/', sync_refresh_api, name='sync-refresh'),
    
    # Static files (in production, use web server)
    path('static/<path:path>', serve, {'document_root': settings.STATIC_ROOT}),
]
