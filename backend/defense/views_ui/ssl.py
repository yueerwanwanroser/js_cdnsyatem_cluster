"""
SSL 证书管理视图
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone
from defense.models import Tenant, SSLCertificate
from defense.serializers import SSLCertificateSerializer
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


@login_required
def ssl_management_view(request):
    """SSL 证书管理页面"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        tenant = Tenant.objects.get(tenant_id=tenant_id)
    except Tenant.DoesNotExist:
        messages.error(request, f'租户 {tenant_id} 不存在')
        return redirect('dashboard')
    
    certs = SSLCertificate.objects.filter(tenant=tenant)
    
    context = {
        'tenant': tenant,
        'certs': certs,
        'active_menu': 'ssl',
    }
    
    return render(request, 'defense/ssl_management.html', context)


@login_required
@require_http_methods(['GET'])
def ssl_list_api(request):
    """获取证书列表 API"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        tenant = Tenant.objects.get(tenant_id=tenant_id)
        certs = SSLCertificate.objects.filter(tenant=tenant)
        serializer = SSLCertificateSerializer(certs, many=True)
        return JsonResponse(serializer.data, safe=False)
    except Exception as e:
        logger.error(f'Error getting SSL certs: {e}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['POST'])
def ssl_upload_api(request):
    """上传证书 API"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        data = json.loads(request.body)
        
        tenant = Tenant.objects.get(tenant_id=tenant_id)
        
        # 生成证书 ID
        cert_id = f"{data.get('domain')}-{timezone.now().timestamp()}"
        
        # 创建证书
        cert = SSLCertificate.objects.create(
            cert_id=cert_id,
            tenant=tenant,
            domain=data.get('domain'),
            cert=data.get('cert'),
            key=data.get('key'),
            expires_at=datetime.fromisoformat(data.get('expires_at')),
        )
        
        serializer = SSLCertificateSerializer(cert)
        return JsonResponse(serializer.data, status=201)
    except Exception as e:
        logger.error(f'Error uploading SSL cert: {e}')
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(['DELETE'])
def ssl_delete_api(request, cert_id):
    """删除证书 API"""
    tenant_id = request.session.get('tenant_id', 'default-tenant')
    
    try:
        cert = get_object_or_404(SSLCertificate, cert_id=cert_id, tenant__tenant_id=tenant_id)
        cert.delete()
        return JsonResponse({'message': '证书已删除'})
    except Exception as e:
        logger.error(f'Error deleting SSL cert: {e}')
        return JsonResponse({'error': str(e)}, status=500)
