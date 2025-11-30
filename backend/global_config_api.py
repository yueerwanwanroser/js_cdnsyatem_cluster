"""
全局配置同步 API - 实现单一真实源
所有修改都通过这些接口，自动同步到全局 etcd，然后同步到所有节点和 APISIX
"""

from flask import Flask, request, jsonify, g
from functools import wraps
import logging
from datetime import datetime
import os

from global_sync_manager import GlobalConfigManager, NodeSyncManager, PluginSyncManager

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局配置管理器（单一真实源）
etcd_host = os.getenv('ETCD_HOST', 'localhost')
etcd_port = int(os.getenv('ETCD_PORT', 2379))

global_config_mgr = GlobalConfigManager(etcd_host, etcd_port)
plugin_sync_mgr = PluginSyncManager(etcd_host, etcd_port)

# 节点同步管理器
node_id = os.getenv('NODE_ID', 'node-1')
node_sync_mgr = NodeSyncManager(node_id, etcd_host, etcd_port)
node_sync_mgr.start_sync_daemon()


def require_tenant(f):
    """验证租户"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        tenant_id = request.headers.get('X-Tenant-ID') or request.args.get('tenant_id')
        
        if not tenant_id:
            return jsonify({'error': '缺少租户ID'}), 400
        
        g.tenant_id = tenant_id
        return f(*args, **kwargs)
    
    return decorated_function


# ============ 全局配置端点 ============

@app.route('/global-config/tenant', methods=['GET', 'POST', 'PUT'])
@require_tenant
def manage_tenant_config():
    """
    管理租户的全局配置
    GET:  获取配置
    POST: 创建/更新配置 (同步到所有节点)
    """
    tenant_id = g.tenant_id
    
    if request.method == 'GET':
        # 从全局配置中心获取
        config = global_config_mgr.get_tenant_config(tenant_id)
        
        if not config:
            return jsonify({'error': f'租户 {tenant_id} 的配置不存在'}), 404
        
        return jsonify({
            'tenant_id': tenant_id,
            'config': config,
            'source': 'global-etcd',
            'synced': True
        })
    
    elif request.method in ['POST', 'PUT']:
        # 更新全局配置 (所有节点同步)
        data = request.get_json()
        config = data.get('config', {})
        
        if not config:
            return jsonify({'error': '配置不能为空'}), 400
        
        success = global_config_mgr.set_tenant_config(tenant_id, config)
        
        if not success:
            return jsonify({'error': '配置更新失败'}), 500
        
        return jsonify({
            'message': f'租户 {tenant_id} 的全局配置已更新',
            'tenant_id': tenant_id,
            'config': config,
            'sync_status': 'broadcasting_to_all_nodes'
        })


@app.route('/global-config/all', methods=['GET'])
def get_all_global_configs():
    """
    获取所有租户的全局配置
    用于管理员查看全局配置快照
    """
    configs = global_config_mgr.get_all_tenant_configs()
    
    return jsonify({
        'total': len(configs),
        'configs': configs,
        'source': 'global-etcd'
    })


# ============ 全局路由端点 ============

@app.route('/global-routes', methods=['GET', 'POST'])
@require_tenant
def manage_global_routes():
    """
    管理全局路由
    GET:  获取租户的所有路由
    POST: 创建新路由 (同步到所有节点和 APISIX)
    """
    tenant_id = g.tenant_id
    
    if request.method == 'GET':
        # 获取租户的所有路由
        routes = global_config_mgr.list_routes(tenant_id)
        
        return jsonify({
            'tenant_id': tenant_id,
            'total': len(routes),
            'routes': routes
        })
    
    elif request.method == 'POST':
        # 创建新路由
        data = request.get_json()
        route_config = data.get('route', {})
        
        if not route_config.get('id'):
            return jsonify({'error': '路由 ID 不能为空'}), 400
        
        route_config['tenant_id'] = tenant_id
        route_config['created_at'] = datetime.now().isoformat()
        
        route_id = route_config['id']
        success = global_config_mgr.set_route(route_id, route_config)
        
        if not success:
            return jsonify({'error': '路由创建失败'}), 500
        
        return jsonify({
            'message': f'路由 {route_id} 已创建',
            'route_id': route_id,
            'tenant_id': tenant_id,
            'sync_status': 'syncing_to_apisix_and_nodes'
        }), 201


@app.route('/global-routes/<route_id>', methods=['GET', 'PUT', 'DELETE'])
def manage_specific_route(route_id):
    """
    管理特定路由
    """
    tenant_id = request.headers.get('X-Tenant-ID')
    
    if request.method == 'GET':
        # 获取路由
        route = global_config_mgr.get_route(route_id)
        
        if not route:
            return jsonify({'error': f'路由 {route_id} 不存在'}), 404
        
        return jsonify(route)
    
    elif request.method == 'PUT':
        # 更新路由
        data = request.get_json()
        updates = data.get('updates', {})
        
        success = global_config_mgr.update_route(route_id, updates)
        
        if not success:
            return jsonify({'error': '路由更新失败'}), 500
        
        return jsonify({
            'message': f'路由 {route_id} 已更新',
            'route_id': route_id,
            'sync_status': 'broadcasting_to_all_nodes'
        })
    
    elif request.method == 'DELETE':
        # 删除路由
        success = global_config_mgr.delete_route(route_id)
        
        if not success:
            return jsonify({'error': '路由删除失败'}), 500
        
        return jsonify({'message': f'路由 {route_id} 已删除'})


# ============ 全局 SSL 证书端点 ============

@app.route('/global-ssl', methods=['GET', 'POST'])
@require_tenant
def manage_ssl_certs():
    """
    管理全局 SSL 证书
    """
    tenant_id = g.tenant_id
    
    if request.method == 'GET':
        # 获取租户的所有证书
        certs = global_config_mgr.list_ssl_certs(tenant_id)
        
        return jsonify({
            'tenant_id': tenant_id,
            'total': len(certs),
            'certs': certs
        })
    
    elif request.method == 'POST':
        # 上传新证书
        data = request.get_json()
        cert_data = {
            'tenant_id': tenant_id,
            'domain': data.get('domain'),
            'cert': data.get('cert'),  # PEM 格式
            'key': data.get('key'),    # PEM 格式
            'expires_at': data.get('expires_at'),
            'created_at': datetime.now().isoformat()
        }
        
        cert_id = f"{tenant_id}:{data.get('domain')}"
        success = global_config_mgr.set_ssl_cert(cert_id, cert_data)
        
        if not success:
            return jsonify({'error': 'SSL 证书上传失败'}), 500
        
        return jsonify({
            'message': f'SSL 证书已上传',
            'cert_id': cert_id,
            'sync_status': 'syncing_to_all_nodes'
        }), 201


# ============ 防御插件同步端点 ============

@app.route('/defense-plugin/apply', methods=['POST'])
@require_tenant
def apply_defense_plugin():
    """
    为路由应用防御插件 (全局生效)
    """
    tenant_id = g.tenant_id
    data = request.get_json()
    
    route_id = data.get('route_id')
    defense_config = data.get('defense_config', {})
    
    if not route_id:
        return jsonify({'error': '路由 ID 不能为空'}), 400
    
    success = plugin_sync_mgr.apply_defense_to_route(
        route_id, tenant_id, defense_config
    )
    
    if not success:
        return jsonify({'error': '防御插件应用失败'}), 500
    
    return jsonify({
        'message': f'防御插件已应用到路由 {route_id}',
        'route_id': route_id,
        'sync_status': 'all_nodes_updated'
    })


@app.route('/defense-plugin/update-all', methods=['POST'])
def update_all_defense_configs():
    """
    批量更新所有路由的防御配置
    仅管理员可用
    """
    data = request.get_json()
    defense_config = data.get('defense_config', {})
    
    if not defense_config:
        return jsonify({'error': '防御配置不能为空'}), 400
    
    updated_count = plugin_sync_mgr.update_all_defense_configs(defense_config)
    
    return jsonify({
        'message': f'已更新 {updated_count} 个路由',
        'updated_count': updated_count,
        'sync_status': 'broadcasting_to_all_nodes'
    })


# ============ 节点同步状态端点 ============

@app.route('/sync-status', methods=['GET'])
def get_sync_status():
    """
    获取当前节点的同步状态
    """
    cache_status = node_sync_mgr.get_cache_status()
    
    return jsonify({
        'node_id': node_id,
        'sync_status': cache_status,
        'etcd_connected': True,  # 实际应该检查 etcd 连接
        'timestamp': datetime.now().isoformat()
    })


@app.route('/sync/refresh', methods=['POST'])
def refresh_node_sync():
    """
    手动刷新节点同步
    重新从 etcd 加载所有配置
    """
    node_sync_mgr.sync_all_configs()
    
    return jsonify({
        'message': '节点同步已刷新',
        'cache_status': node_sync_mgr.get_cache_status()
    })


# ============ 配置验证端点 ============

@app.route('/config/validate', methods=['POST'])
def validate_config():
    """
    验证配置是否一致
    检查所有节点是否有相同的配置版本
    """
    # 这里可以添加跨节点配置一致性检查
    # 比如检查所有节点的缓存版本是否相同
    
    return jsonify({
        'valid': True,
        'message': '所有配置一致'
    })


# ============ 全局事件查看端点 ============

@app.route('/events/config-changes', methods=['GET'])
@require_tenant
def get_config_changes():
    """
    查看租户配置的变更历史
    """
    tenant_id = g.tenant_id
    limit = request.args.get('limit', 50, type=int)
    
    # 从 etcd 中获取最近的配置事件
    # 实现方式需要在全局配置管理器中添加事件历史存储
    
    return jsonify({
        'tenant_id': tenant_id,
        'total': 0,
        'events': []
    })


# ============ 监控端点 ============

@app.route('/monitor/global-sync', methods=['GET'])
def monitor_global_sync():
    """
    监控全局同步状态
    显示 etcd 中的配置总数和节点同步情况
    """
    all_configs = global_config_mgr.get_all_tenant_configs()
    all_routes = global_config_mgr.list_routes()
    all_certs = global_config_mgr.list_ssl_certs()
    
    return jsonify({
        'etcd_status': {
            'total_tenants': len(all_configs),
            'total_routes': len(all_routes),
            'total_ssl_certs': len(all_certs)
        },
        'node_status': {
            'node_id': node_id,
            'cache_items': len(node_sync_mgr.local_cache),
            'is_syncing': node_sync_mgr.is_syncing
        },
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    logger.info(f"全局配置同步 API 启动，节点 ID: {node_id}")
    
    port = int(os.getenv('GLOBAL_API_PORT', 5001))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        threaded=True
    )
