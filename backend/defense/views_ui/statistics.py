"""
统计分析视图
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from defense.models import Tenant, SyncLog
import logging

logger = logging.getLogger(__name__)


@login_required
def statistics_view(request):
    """统计分析页面"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        tenant = Tenant.objects.get(tenant_id=tenant_id)
    except Tenant.DoesNotExist:
        messages.error(request, f'租户 {tenant_id} 不存在')
        return redirect('dashboard')
    
    context = {
        'tenant': tenant,
        'active_menu': 'statistics',
    }
    
    return render(request, 'defense/statistics.html', context)


@login_required
@require_http_methods(['GET'])
def statistics_data_api(request):
    """获取统计数据 API"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        tenant = Tenant.objects.get(tenant_id=tenant_id)
        
        # 获取时间范围
        days = int(request.GET.get('days', 7))
        start_date = timezone.now() - timedelta(days=days)
        
        # 查询统计数据
        logs = SyncLog.objects.filter(
            tenant=tenant,
            created_at__gte=start_date
        )
        
        # 按日期分组统计
        daily_stats = {}
        for log in logs:
            date = log.created_at.date()
            if date not in daily_stats:
                daily_stats[date] = {
                    'date': str(date),
                    'total': 0,
                    'blocked': 0,
                    'allowed': 0,
                }
            daily_stats[date]['total'] += 1
            if log.status == 'blocked':
                daily_stats[date]['blocked'] += 1
            else:
                daily_stats[date]['allowed'] += 1
        
        # 转换为列表并排序
        stats_list = sorted(daily_stats.values(), key=lambda x: x['date'])
        
        # 计算总体统计
        total_requests = logs.count()
        blocked_requests = logs.filter(status='blocked').count()
        allowed_requests = logs.filter(status='allowed').count()
        
        return JsonResponse({
            'daily_stats': stats_list,
            'total_requests': total_requests,
            'blocked_requests': blocked_requests,
            'allowed_requests': allowed_requests,
            'block_rate': round(blocked_requests / total_requests * 100, 2) if total_requests > 0 else 0,
        })
    except Exception as e:
        logger.error(f'Error getting statistics: {e}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['GET'])
def top_blocked_ips_api(request):
    """获取被阻止最多的 IP 列表 API"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        tenant = Tenant.objects.get(tenant_id=tenant_id)
        
        # 获取被阻止次数最多的 IP
        top_ips = SyncLog.objects.filter(
            tenant=tenant,
            status='blocked'
        ).values('client_ip').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return JsonResponse(list(top_ips), safe=False)
    except Exception as e:
        logger.error(f'Error getting top blocked IPs: {e}')
        return JsonResponse({'error': str(e)}, status=500)
