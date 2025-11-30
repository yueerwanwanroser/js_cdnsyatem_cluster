"""
路由管理视图 - 管理 API 路由和 APISIX 配置
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from defense.models import Tenant, Route
from defense.serializers import RouteSerializer
from defense.services import GlobalConfigManager
import logging
import json

logger = logging.getLogger(__name__)


@login_required
def route_management_view(request):
    """路由管理页面"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        tenant = Tenant.objects.get(tenant_id=tenant_id)
    except Tenant.DoesNotExist:
        messages.error(request, f'租户 {tenant_id} 不存在')
        return redirect('dashboard')
    
    routes = Route.objects.filter(tenant=tenant)
    
    context = {
        'tenant': tenant,
        'routes': routes,
        'active_menu': 'routes',
    }
    
    return render(request, 'defense/route_management.html', context)


@login_required
@require_http_methods(['GET'])
def routes_list_api(request):
    """获取路由列表 API"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        tenant = Tenant.objects.get(tenant_id=tenant_id)
        routes = Route.objects.filter(tenant=tenant)
        serializer = RouteSerializer(routes, many=True)
        return JsonResponse(serializer.data, safe=False)
    except Exception as e:
        logger.error(f'Error getting routes: {e}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def route_create_api(request):
    """创建路由 API"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        data = json.loads(request.body)
        
        tenant = Tenant.objects.get(tenant_id=tenant_id)
        
        # 检查路由 ID 是否存在
        route_id = data.get('route_id')
        if Route.objects.filter(route_id=route_id).exists():
            return JsonResponse({'error': '路由 ID 已存在'}, status=400)
        
        # 创建路由
        route = Route.objects.create(
            route_id=route_id,
            tenant=tenant,
            path=data.get('path'),
            upstream=data.get('upstream'),
            methods=data.get('methods', ['GET', 'POST']),
            enabled=data.get('enabled', True),
        )
        
        # 同步到 etcd
        try:
            config_mgr = GlobalConfigManager()
            config_mgr.set_route(route_id, {
                'id': route_id,
                'path': route.path,
                'upstream': route.upstream,
                'methods': route.methods,
                'enabled': route.enabled,
            })
        except Exception as e:
            logger.warning(f'Failed to sync route to etcd: {e}')
        
        serializer = RouteSerializer(route)
        return JsonResponse(serializer.data, status=201)
    except Exception as e:
        logger.error(f'Error creating route: {e}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['PUT'])
def route_update_api(request, route_id):
    """更新路由 API"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        data = json.loads(request.body)
        
        route = get_object_or_404(Route, route_id=route_id, tenant__tenant_id=tenant_id)
        
        # 更新字段
        if 'path' in data:
            route.path = data['path']
        if 'upstream' in data:
            route.upstream = data['upstream']
        if 'methods' in data:
            route.methods = data['methods']
        if 'enabled' in data:
            route.enabled = bool(data['enabled'])
        
        route.version += 1
        route.save()
        
        # 同步到 etcd
        try:
            config_mgr = GlobalConfigManager()
            config_mgr.set_route(route_id, {
                'id': route_id,
                'path': route.path,
                'upstream': route.upstream,
                'methods': route.methods,
                'enabled': route.enabled,
            })
        except Exception as e:
            logger.warning(f'Failed to sync route to etcd: {e}')
        
        serializer = RouteSerializer(route)
        return JsonResponse(serializer.data)
    except Exception as e:
        logger.error(f'Error updating route: {e}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['DELETE'])
def route_delete_api(request, route_id):
    """删除路由 API"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        route = get_object_or_404(Route, route_id=route_id, tenant__tenant_id=tenant_id)
        
        # 从 etcd 删除
        try:
            config_mgr = GlobalConfigManager()
            config_mgr.delete_route(route_id)
        except Exception as e:
            logger.warning(f'Failed to delete route from etcd: {e}')
        
        route.delete()
        return JsonResponse({'message': '路由已删除'})
    except Exception as e:
        logger.error(f'Error deleting route: {e}')
        return JsonResponse({'error': str(e)}, status=500)
