"""
认证和首页视图
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from defense.models import Tenant


@require_http_methods(['GET', 'POST'])
def login_view(request):
    """登录视图"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        tenant_id = request.POST.get('tenant_id', 'default-tenant')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            request.session['tenant_id'] = tenant_id
            return redirect('dashboard')
        else:
            error = '用户名或密码错误'
            return render(request, 'login.html', {'error': error})
    
    return render(request, 'login.html')


@require_http_methods(['GET'])
def logout_view(request):
    """登出视图"""
    logout(request)
    return redirect('login')


@login_required
def index_view(request):
    """首页重定向到仪表盘"""
    return redirect('dashboard')


@require_http_methods(['POST'])
def tenant_switch_api(request):
    """切换租户 API"""
    import json
    
    try:
        data = json.loads(request.body)
        tenant_id = data.get('tenant_id', 'default-tenant')
        
        # 验证租户是否存在或创建
        tenant, created = Tenant.objects.get_or_create(
            tenant_id=tenant_id,
            defaults={'name': tenant_id}
        )
        
        request.session['tenant_id'] = tenant_id
        return JsonResponse({
            'message': f'已切换到租户: {tenant_id}',
            'status': 'success'
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=400)
