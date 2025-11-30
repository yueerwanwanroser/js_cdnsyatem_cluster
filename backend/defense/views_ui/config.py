"""
配置管理视图 - 管理租户全局配置
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from defense.models import Tenant, TenantConfig
from defense.serializers import TenantConfigSerializer
from defense.services import GlobalConfigManager
import logging

logger = logging.getLogger(__name__)


@login_required
def config_management_view(request):
    """配置管理页面"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        tenant = Tenant.objects.get(tenant_id=tenant_id)
    except Tenant.DoesNotExist:
        messages.error(request, f'租户 {tenant_id} 不存在')
        return redirect('dashboard')
    
    # 获取或创建配置
    config, created = TenantConfig.objects.get_or_create(tenant=tenant)
    
    if request.method == 'POST':
        # 处理配置更新
        try:
            config.rate_limit = int(request.POST.get('rate_limit', config.rate_limit))
            config.threat_threshold = int(request.POST.get('threat_threshold', config.threat_threshold))
            config.enabled_defense = request.POST.get('enabled_defense') == 'on'
            config.js_challenge = request.POST.get('js_challenge') == 'on'
            config.bot_detection = request.POST.get('bot_detection') == 'on'
            config.version += 1
            config.save()
            
            # 同步到 etcd
            try:
                config_mgr = GlobalConfigManager()
                config_mgr.set_tenant_config(tenant_id, {
                    'rate_limit': config.rate_limit,
                    'threat_threshold': config.threat_threshold,
                    'enabled_defense': config.enabled_defense,
                    'js_challenge': config.js_challenge,
                    'bot_detection': config.bot_detection,
                })
            except Exception as e:
                logger.error(f'Failed to sync config to etcd: {e}')
            
            messages.success(request, '配置已更新')
            return redirect('config_management')
        except Exception as e:
            logger.error(f'Error updating config: {e}')
            messages.error(request, f'更新失败: {str(e)}')
    
    context = {
        'tenant': tenant,
        'config': config,
        'active_menu': 'config',
    }
    
    return render(request, 'defense/config_management.html', context)


@login_required
@require_http_methods(['GET'])
def config_api(request):
    """获取配置 API"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        tenant = Tenant.objects.get(tenant_id=tenant_id)
        config = tenant.config
        serializer = TenantConfigSerializer(config)
        return JsonResponse(serializer.data)
    except Exception as e:
        logger.error(f'Error getting config: {e}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def config_update_api(request):
    """更新配置 API"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        import json
        data = json.loads(request.body)
        
        tenant = Tenant.objects.get(tenant_id=tenant_id)
        config = tenant.config
        
        # 更新字段
        if 'rate_limit' in data:
            config.rate_limit = int(data['rate_limit'])
        if 'threat_threshold' in data:
            config.threat_threshold = int(data['threat_threshold'])
        if 'enabled_defense' in data:
            config.enabled_defense = bool(data['enabled_defense'])
        if 'js_challenge' in data:
            config.js_challenge = bool(data['js_challenge'])
        if 'bot_detection' in data:
            config.bot_detection = bool(data['bot_detection'])
        
        config.version += 1
        config.save()
        
        # 同步到 etcd
        try:
            config_mgr = GlobalConfigManager()
            config_mgr.set_tenant_config(tenant_id, {
                'rate_limit': config.rate_limit,
                'threat_threshold': config.threat_threshold,
                'enabled_defense': config.enabled_defense,
                'js_challenge': config.js_challenge,
                'bot_detection': config.bot_detection,
            })
        except Exception as e:
            logger.warning(f'Failed to sync config to etcd: {e}')
        
        serializer = TenantConfigSerializer(config)
        return JsonResponse(serializer.data)
    except Exception as e:
        logger.error(f'Error updating config: {e}')
        return JsonResponse({'error': str(e)}, status=500)
