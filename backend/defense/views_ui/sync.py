"""
同步监控视图
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from defense.services import GlobalConfigManager
from defense.models import Tenant
import logging

logger = logging.getLogger(__name__)


@login_required
def sync_monitoring_view(request):
    """同步监控页面"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        tenant = Tenant.objects.get(tenant_id=tenant_id)
    except Tenant.DoesNotExist:
        messages.error(request, f'租户 {tenant_id} 不存在')
        return redirect('dashboard')
    
    context = {
        'tenant': tenant,
        'active_menu': 'sync',
    }
    
    return render(request, 'defense/sync_monitoring.html', context)


@login_required
@require_http_methods(['GET'])
def sync_status_api(request):
    """获取同步状态 API"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        config_mgr = GlobalConfigManager()
        
        # 检查 etcd 连接
        etcd_connected = config_mgr.check_etcd_connection()
        
        # 获取最后同步时间
        last_sync = config_mgr.get_last_sync_time(tenant_id) or 'Never'
        
        return JsonResponse({
            'node_id': 'node-1',
            'etcd_connected': etcd_connected,
            'last_sync': last_sync,
            'status': 'healthy' if etcd_connected else 'unhealthy',
        })
    except Exception as e:
        logger.error(f'Error getting sync status: {e}')
        return JsonResponse({
            'node_id': 'node-1',
            'etcd_connected': False,
            'last_sync': 'Unknown',
            'status': 'unhealthy',
            'error': str(e),
        })


@login_required
@require_http_methods(['POST'])
def sync_refresh_api(request):
    """刷新同步 API"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        config_mgr = GlobalConfigManager()
        
        # 强制同步
        config_mgr.force_sync(tenant_id)
        
        return JsonResponse({
            'message': '已刷新同步',
            'status': 'success',
        })
    except Exception as e:
        logger.error(f'Error refreshing sync: {e}')
        return JsonResponse({
            'error': str(e),
            'status': 'error',
        }, status=500)
