"""
URL configuration for CDN Defense System.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.documentation import include_docs_urls

# Import viewsets
from defense.views import (
    TenantConfigViewSet,
    RouteViewSet,
    SSLCertificateViewSet,
    DefensePluginViewSet,
    SyncStatusView,
    MonitoringView,
)

# Create router for API endpoints
router = DefaultRouter()
router.register(r'config/tenant', TenantConfigViewSet, basename='tenant-config')
router.register(r'routes', RouteViewSet, basename='routes')
router.register(r'ssl', SSLCertificateViewSet, basename='ssl')
router.register(r'defense-plugin', DefensePluginViewSet, basename='defense-plugin')

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('api/docs/', include_docs_urls(title='CDN Defense System API')),
    
    # API Endpoints
    path('api/v1/', include(router.urls)),
    
    # Custom endpoints
    path('api/v1/sync-status/', SyncStatusView.as_view(), name='sync-status'),
    path('api/v1/monitor/global-sync/', MonitoringView.as_view(), name='monitoring'),
]
