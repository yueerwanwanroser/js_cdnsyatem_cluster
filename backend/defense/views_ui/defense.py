"""
防御策略管理视图
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from defense.models import Tenant, Route, DefensePolicy
from defense.serializers import DefensePolicySerializer
import logging
import json

logger = logging.getLogger(__name__)


@login_required
def defense_strategy_view(request):
    """防御策略管理页面"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        tenant = Tenant.objects.get(tenant_id=tenant_id)
    except Tenant.DoesNotExist:
        messages.error(request, f'租户 {tenant_id} 不存在')
        return redirect('dashboard')
    
    # 获取路由列表
    routes = Route.objects.filter(tenant=tenant, enabled=True)
    policies = DefensePolicy.objects.filter(tenant=tenant)
    
    context = {
        'tenant': tenant,
        'routes': routes,
        'policies': policies,
        'active_menu': 'defense',
    }
    
    return render(request, 'defense/defense_strategy.html', context)


@login_required
@require_http_methods(['GET'])
def defense_policies_api(request):
    """获取防御策略列表 API"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        tenant = Tenant.objects.get(tenant_id=tenant_id)
        policies = DefensePolicy.objects.filter(tenant=tenant)
        serializer = DefensePolicySerializer(policies, many=True)
        return JsonResponse(serializer.data, safe=False)
    except Exception as e:
        logger.error(f'Error getting defense policies: {e}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def defense_policy_create_api(request):
    """创建防御策略 API"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        data = json.loads(request.body)
        
        tenant = Tenant.objects.get(tenant_id=tenant_id)
        route = Route.objects.get(route_id=data.get('route_id'), tenant=tenant)
        
        policy = DefensePolicy.objects.create(
            tenant=tenant,
            route=route,
            threat_threshold=data.get('threat_threshold', 75),
            challenge_type=data.get('challenge_type', 'js'),
            enabled=data.get('enabled', True),
        )
        
        serializer = DefensePolicySerializer(policy)
        return JsonResponse(serializer.data, status=201)
    except Exception as e:
        logger.error(f'Error creating defense policy: {e}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['PUT'])
def defense_policy_update_api(request, policy_id):
    """更新防御策略 API"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        data = json.loads(request.body)
        
        policy = DefensePolicy.objects.get(id=policy_id, tenant__tenant_id=tenant_id)
        
        if 'threat_threshold' in data:
            policy.threat_threshold = data['threat_threshold']
        if 'challenge_type' in data:
            policy.challenge_type = data['challenge_type']
        if 'enabled' in data:
            policy.enabled = bool(data['enabled'])
        
        policy.save()
        
        serializer = DefensePolicySerializer(policy)
        return JsonResponse(serializer.data)
    except Exception as e:
        logger.error(f'Error updating defense policy: {e}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['DELETE'])
def defense_policy_delete_api(request, policy_id):
    """删除防御策略 API"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        policy = DefensePolicy.objects.get(id=policy_id, tenant__tenant_id=tenant_id)
        policy.delete()
        return JsonResponse({'message': '防御策略已删除'})
    except Exception as e:
        logger.error(f'Error deleting defense policy: {e}')
        return JsonResponse({'error': str(e)}, status=500)
