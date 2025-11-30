"""
仪表盘视图 - 统计和系统状态概览
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from defense.models import Tenant, TenantConfig, Route, SyncLog
from defense.services import GlobalConfigManager
import logging

logger = logging.getLogger(__name__)


@login_required
def dashboard_view(request):
    """主仪表盘页面"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        tenant = Tenant.objects.get(tenant_id=tenant_id)
    except Tenant.DoesNotExist:
        tenant = None
    
    # 获取统计数据
    total_requests = SyncLog.objects.filter(
        tenant__tenant_id=tenant_id
    ).count() if tenant else 0
    
    blocked_requests = SyncLog.objects.filter(
        tenant__tenant_id=tenant_id,
        status='blocked'
    ).count() if tenant else 0
    
    # 计算平均威胁分数
    routes = Route.objects.filter(tenant=tenant) if tenant else []
    avg_threat_score = 65  # 默认值
    
    # 系统健康状态
    system_health = 'healthy'
    try:
        config_mgr = GlobalConfigManager()
        if not config_mgr.check_etcd_connection():
            system_health = 'warning'
    except Exception as e:
        logger.error(f'Failed to check system health: {e}')
        system_health = 'unhealthy'
    
    context = {
        'tenant': tenant,
        'tenant_id': tenant_id,
        'total_requests': total_requests,
        'blocked_requests': blocked_requests,
        'avg_threat_score': avg_threat_score,
        'system_health': system_health,
        'active_menu': 'dashboard',
    }
    
    return render(request, 'defense/dashboard.html', context)


@login_required
@require_http_methods(['GET'])
def dashboard_stats_api(request):
    """获取实时统计数据 (AJAX)"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        total_requests = SyncLog.objects.filter(
            tenant__tenant_id=tenant_id
        ).count()
        
        blocked_requests = SyncLog.objects.filter(
            tenant__tenant_id=tenant_id,
            status='blocked'
        ).count()
        
        return JsonResponse({
            'total_requests': total_requests,
            'blocked_requests': blocked_requests,
            'avg_threat_score': 65,
            'system_health': 'healthy',
        })
    except Exception as e:
        logger.error(f'Error getting stats: {e}')
        return JsonResponse({'error': str(e)}, status=500)
