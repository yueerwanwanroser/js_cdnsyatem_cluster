"""
CDN 防御系统 - 前端管理 API 网关
汇总所有后端 API，提供统一的前端接口

前端直接调用此网关，无需知道内部实现细节
"""

from flask import Flask, request, jsonify, g
from flask_cors import CORS
import requests
import logging
import os
from functools import wraps
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)  # 启用 CORS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 后端服务地址
DEFENSE_API_URL = os.getenv('DEFENSE_API_URL', 'http://localhost:5000')
GLOBAL_CONFIG_API_URL = os.getenv('GLOBAL_CONFIG_API_URL', 'http://localhost:5001')

# 前端 API 端口
FRONTEND_API_PORT = int(os.getenv('FRONTEND_API_PORT', 5002))


def proxy_to_backend(backend_url):
    """代理请求到后端服务"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # 获取租户 ID
                tenant_id = request.headers.get('X-Tenant-ID') or request.args.get('tenant_id')
                if not tenant_id:
                    return jsonify({'error': '缺少租户ID'}), 400
                
                # 准备请求头
                headers = {
                    'X-Tenant-ID': tenant_id,
                    'Content-Type': 'application/json'
                }
                
                # 获取请求数据
                data = request.get_json() if request.method in ['POST', 'PUT'] else None
                
                # 调用后端 API
                if request.method == 'GET':
                    response = requests.get(backend_url, headers=headers, params=request.args)
                elif request.method == 'POST':
                    response = requests.post(backend_url, headers=headers, json=data)
                elif request.method == 'PUT':
                    response = requests.put(backend_url, headers=headers, json=data)
                elif request.method == 'DELETE':
                    response = requests.delete(backend_url, headers=headers)
                
                return jsonify(response.json()), response.status_code
            
            except Exception as e:
                logger.error(f'后端请求失败: {str(e)}')
                return jsonify({'error': f'后端服务错误: {str(e)}'}), 500
        
        return decorated_function
    return decorator


# ============ 配置管理 API (前端聚合) ============

@app.route('/api/config', methods=['GET', 'POST', 'PUT'])
def manage_config():
    """
    配置管理统一入口
    GET: 获取当前配置
    POST/PUT: 修改配置
    """
    tenant_id = request.headers.get('X-Tenant-ID')
    if not tenant_id:
        return jsonify({'error': '缺少租户ID'}), 400
    
    try:
        headers = {'X-Tenant-ID': tenant_id, 'Content-Type': 'application/json'}
        
        if request.method == 'GET':
            # 优先从全局配置 API 获取
            response = requests.get(
                f'{GLOBAL_CONFIG_API_URL}/global-config/tenant',
                headers=headers
            )
        else:
            # 更新配置
            data = request.get_json()
            response = requests.post(
                f'{GLOBAL_CONFIG_API_URL}/global-config/tenant',
                headers=headers,
                json=data
            )
        
        return jsonify(response.json()), response.status_code
    
    except Exception as e:
        logger.error(f'配置 API 错误: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/config/all', methods=['GET'])
def get_all_configs():
    """获取所有租户配置"""
    try:
        response = requests.get(
            f'{GLOBAL_CONFIG_API_URL}/global-config/all'
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ 路由管理 API ============

@app.route('/api/routes', methods=['GET', 'POST'])
def manage_routes():
    """路由列表和创建"""
    tenant_id = request.headers.get('X-Tenant-ID')
    if not tenant_id:
        return jsonify({'error': '缺少租户ID'}), 400
    
    try:
        headers = {'X-Tenant-ID': tenant_id, 'Content-Type': 'application/json'}
        
        if request.method == 'GET':
            response = requests.get(
                f'{GLOBAL_CONFIG_API_URL}/global-routes',
                headers=headers
            )
        else:
            data = request.get_json()
            response = requests.post(
                f'{GLOBAL_CONFIG_API_URL}/global-routes',
                headers=headers,
                json=data
            )
        
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/routes/<route_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_specific_route(route_id):
    """路由详情、更新、删除"""
    tenant_id = request.headers.get('X-Tenant-ID')
    
    try:
        headers = {'Content-Type': 'application/json'}
        if tenant_id:
            headers['X-Tenant-ID'] = tenant_id
        
        url = f'{GLOBAL_CONFIG_API_URL}/global-routes/{route_id}'
        
        if request.method == 'GET':
            response = requests.get(url, headers=headers)
        elif request.method == 'PUT':
            data = request.get_json()
            response = requests.put(url, headers=headers, json=data)
        elif request.method == 'DELETE':
            response = requests.delete(url, headers=headers)
        
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ SSL 证书管理 API ============

@app.route('/api/ssl', methods=['GET', 'POST'])
def manage_ssl():
    """SSL 证书列表和上传"""
    tenant_id = request.headers.get('X-Tenant-ID')
    if not tenant_id:
        return jsonify({'error': '缺少租户ID'}), 400
    
    try:
        headers = {'X-Tenant-ID': tenant_id, 'Content-Type': 'application/json'}
        
        if request.method == 'GET':
            response = requests.get(
                f'{GLOBAL_CONFIG_API_URL}/global-ssl',
                headers=headers
            )
        else:
            data = request.get_json()
            response = requests.post(
                f'{GLOBAL_CONFIG_API_URL}/global-ssl',
                headers=headers,
                json=data
            )
        
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ 防御管理 API ============

@app.route('/api/defense/enable', methods=['POST'])
def enable_defense():
    """为路由启用防御"""
    tenant_id = request.headers.get('X-Tenant-ID')
    if not tenant_id:
        return jsonify({'error': '缺少租户ID'}), 400
    
    try:
        data = request.get_json()
        response = requests.post(
            f'{GLOBAL_CONFIG_API_URL}/defense-plugin/apply',
            headers={'X-Tenant-ID': tenant_id, 'Content-Type': 'application/json'},
            json=data
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/defense/update-all', methods=['POST'])
def update_all_defense():
    """批量更新防御配置"""
    try:
        data = request.get_json()
        response = requests.post(
            f'{GLOBAL_CONFIG_API_URL}/defense-plugin/update-all',
            headers={'Content-Type': 'application/json'},
            json=data
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ 防御分析 API ============

@app.route('/api/analyze', methods=['POST'])
def analyze_request():
    """分析请求"""
    tenant_id = request.headers.get('X-Tenant-ID')
    if not tenant_id:
        return jsonify({'error': '缺少租户ID'}), 400
    
    try:
        data = request.get_json()
        response = requests.post(
            f'{DEFENSE_API_URL}/analyze',
            headers={'X-Tenant-ID': tenant_id, 'Content-Type': 'application/json'},
            json=data
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ 统计和日志 API ============

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """获取统计信息"""
    tenant_id = request.headers.get('X-Tenant-ID')
    if not tenant_id:
        return jsonify({'error': '缺少租户ID'}), 400
    
    try:
        response = requests.get(
            f'{DEFENSE_API_URL}/statistics',
            headers={'X-Tenant-ID': tenant_id}
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/logs', methods=['GET'])
def get_logs():
    """获取日志"""
    tenant_id = request.headers.get('X-Tenant-ID')
    if not tenant_id:
        return jsonify({'error': '缺少租户ID'}), 400
    
    try:
        response = requests.get(
            f'{DEFENSE_API_URL}/logs',
            headers={'X-Tenant-ID': tenant_id},
            params=request.args
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ 监控和诊断 API ============

@app.route('/api/sync/status', methods=['GET'])
def get_sync_status():
    """获取同步状态"""
    try:
        response = requests.get(
            f'{GLOBAL_CONFIG_API_URL}/sync-status'
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sync/refresh', methods=['POST'])
def refresh_sync():
    """手动刷新同步"""
    try:
        response = requests.post(
            f'{GLOBAL_CONFIG_API_URL}/sync/refresh'
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/monitor', methods=['GET'])
def get_monitor_info():
    """获取全局监控信息"""
    try:
        response = requests.get(
            f'{GLOBAL_CONFIG_API_URL}/monitor/global-sync'
        )
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ 系统健康检查 ============

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    try:
        # 检查防御 API
        defense_ok = False
        try:
            r = requests.get(f'{DEFENSE_API_URL}/health', timeout=2)
            defense_ok = r.status_code == 200
        except:
            pass
        
        # 检查全局配置 API
        config_ok = False
        try:
            r = requests.get(f'{GLOBAL_CONFIG_API_URL}/sync-status', timeout=2)
            config_ok = r.status_code == 200
        except:
            pass
        
        status = 'healthy' if defense_ok and config_ok else 'degraded'
        
        return jsonify({
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'services': {
                'defense_api': 'ok' if defense_ok else 'down',
                'config_api': 'ok' if config_ok else 'down'
            }
        })
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500


# ============ 服务信息 ============

@app.route('/api/info', methods=['GET'])
def get_info():
    """获取服务信息"""
    return jsonify({
        'service': 'CDN Defense System - Frontend API Gateway',
        'version': '2.0',
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            'config': '/api/config',
            'routes': '/api/routes',
            'ssl': '/api/ssl',
            'defense': '/api/defense',
            'analyze': '/api/analyze',
            'statistics': '/api/statistics',
            'logs': '/api/logs',
            'sync': '/api/sync',
            'monitor': '/api/monitor',
            'health': '/api/health'
        }
    })


# ============ 错误处理 ============

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '端点未找到'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': '服务器内部错误'}), 500


if __name__ == '__main__':
    logger.info('CDN 防御系统 前端 API 网关启动')
    logger.info(f'防御 API: {DEFENSE_API_URL}')
    logger.info(f'全局配置 API: {GLOBAL_CONFIG_API_URL}')
    
    app.run(
        host='0.0.0.0',
        port=FRONTEND_API_PORT,
        debug=False,
        threaded=True
    )
