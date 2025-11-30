"""
全局路由和配置同步管理器
在 etcd 中维护单一真实源，所有节点自动同步
"""

import etcd3
import json
import logging
from typing import Dict, List, Optional
import time
from threading import Thread, Lock

logger = logging.getLogger(__name__)


class GlobalConfigManager:
    """全局配置管理器 - 所有配置的单一真实源"""
    
    def __init__(self, etcd_host='localhost', etcd_port=2379):
        self.etcd = etcd3.client(host=etcd_host, port=etcd_port)
        self.config_lock = Lock()
        self.config_prefix = '/cdn-defense/config/'
        self.route_prefix = '/cdn-defense/routes/'
        self.ssl_prefix = '/cdn-defense/ssl/'
    
    # ============ 配置管理 ============
    
    def set_tenant_config(self, tenant_id: str, config: Dict) -> bool:
        """
        设置租户配置 (全局同步)
        所有节点都会自动看到此配置
        """
        with self.config_lock:
            key = f"{self.config_prefix}{tenant_id}"
            
            try:
                self.etcd.put(key, json.dumps({
                    'config': config,
                    'updated_at': time.time(),
                    'version': int(time.time() * 1000)  # 版本号
                }))
                
                logger.info(f"全局配置已更新: tenant={tenant_id}")
                
                # 发布配置变更事件
                self._publish_config_change('config_update', tenant_id, config)
                
                return True
            except Exception as e:
                logger.error(f"配置更新失败: {e}")
                return False
    
    def get_tenant_config(self, tenant_id: str) -> Optional[Dict]:
        """获取租户配置"""
        key = f"{self.config_prefix}{tenant_id}"
        
        try:
            value = self.etcd.get(key)
            if value[0]:
                data = json.loads(value[0])
                return data.get('config')
        except Exception as e:
            logger.error(f"获取配置失败: {e}")
        
        return None
    
    def get_all_tenant_configs(self) -> Dict[str, Dict]:
        """获取所有租户配置"""
        configs = {}
        
        try:
            for value, metadata in self.etcd.get_prefix(self.config_prefix):
                if value:
                    data = json.loads(value.decode())
                    tenant_id = metadata.key.decode().replace(self.config_prefix, '')
                    configs[tenant_id] = data
        except Exception as e:
            logger.error(f"获取所有配置失败: {e}")
        
        return configs
    
    def watch_config_changes(self, callback):
        """
        监听配置变更
        当任何节点修改配置时，所有节点都会收到通知
        """
        watch_iter = self.etcd.watch_prefix(self.config_prefix)
        
        for response in watch_iter:
            if not response.canceled:
                for event in response.events:
                    if event.value:
                        data = json.loads(event.value)
                        tenant_id = event.key.decode().replace(self.config_prefix, '')
                        callback('config_update', tenant_id, data)
                    else:
                        tenant_id = event.key.decode().replace(self.config_prefix, '')
                        callback('config_delete', tenant_id, None)
    
    # ============ 路由管理 ============
    
    def set_route(self, route_id: str, route_config: Dict) -> bool:
        """
        设置路由配置 (全局同步)
        APISIX 会自动从 etcd 同步此路由
        """
        with self.config_lock:
            key = f"{self.route_prefix}{route_id}"
            
            try:
                self.etcd.put(key, json.dumps({
                    'route': route_config,
                    'created_at': route_config.get('created_at', time.time()),
                    'updated_at': time.time(),
                    'version': int(time.time() * 1000)
                }))
                
                logger.info(f"全局路由已更新: route_id={route_id}")
                
                # 发布路由变更事件
                self._publish_route_change('route_update', route_id, route_config)
                
                return True
            except Exception as e:
                logger.error(f"路由更新失败: {e}")
                return False
    
    def get_route(self, route_id: str) -> Optional[Dict]:
        """获取路由配置"""
        key = f"{self.route_prefix}{route_id}"
        
        try:
            value = self.etcd.get(key)
            if value[0]:
                data = json.loads(value[0])
                return data.get('route')
        except Exception as e:
            logger.error(f"获取路由失败: {e}")
        
        return None
    
    def list_routes(self, tenant_id: str = None) -> List[Dict]:
        """
        列出所有路由 (或特定租户的路由)
        """
        routes = []
        
        try:
            for value, metadata in self.etcd.get_prefix(self.route_prefix):
                if value:
                    data = json.loads(value.decode())
                    route = data.get('route', {})
                    
                    # 按租户过滤
                    if tenant_id is None or route.get('tenant_id') == tenant_id:
                        routes.append(route)
        except Exception as e:
            logger.error(f"获取路由列表失败: {e}")
        
        return routes
    
    def update_route(self, route_id: str, updates: Dict) -> bool:
        """
        更新路由配置 (增量更新)
        """
        route = self.get_route(route_id)
        if not route:
            return False
        
        route.update(updates)
        return self.set_route(route_id, route)
    
    def delete_route(self, route_id: str) -> bool:
        """删除路由"""
        key = f"{self.route_prefix}{route_id}"
        
        try:
            self.etcd.delete(key)
            logger.info(f"路由已删除: route_id={route_id}")
            self._publish_route_change('route_delete', route_id, None)
            return True
        except Exception as e:
            logger.error(f"删除路由失败: {e}")
            return False
    
    # ============ SSL/TLS 管理 ============
    
    def set_ssl_cert(self, cert_id: str, cert_data: Dict) -> bool:
        """
        设置 SSL 证书 (全局同步)
        """
        with self.config_lock:
            key = f"{self.ssl_prefix}{cert_id}"
            
            try:
                self.etcd.put(key, json.dumps({
                    'cert': cert_data,
                    'updated_at': time.time(),
                    'version': int(time.time() * 1000)
                }))
                
                logger.info(f"SSL 证书已更新: cert_id={cert_id}")
                
                # 发布证书变更事件
                self._publish_ssl_change('ssl_update', cert_id, cert_data)
                
                return True
            except Exception as e:
                logger.error(f"SSL 证书更新失败: {e}")
                return False
    
    def get_ssl_cert(self, cert_id: str) -> Optional[Dict]:
        """获取 SSL 证书"""
        key = f"{self.ssl_prefix}{cert_id}"
        
        try:
            value = self.etcd.get(key)
            if value[0]:
                data = json.loads(value[0])
                return data.get('cert')
        except Exception as e:
            logger.error(f"获取 SSL 证书失败: {e}")
        
        return None
    
    def list_ssl_certs(self, tenant_id: str = None) -> List[Dict]:
        """列出所有 SSL 证书"""
        certs = []
        
        try:
            for value, metadata in self.etcd.get_prefix(self.ssl_prefix):
                if value:
                    data = json.loads(value.decode())
                    cert = data.get('cert', {})
                    
                    if tenant_id is None or cert.get('tenant_id') == tenant_id:
                        certs.append(cert)
        except Exception as e:
            logger.error(f"获取 SSL 证书列表失败: {e}")
        
        return certs
    
    # ============ 防御插件管理 ============
    
    def enable_defense_plugin(self, route_id: str, plugin_config: Dict) -> bool:
        """
        为路由启用防御插件 (全局生效)
        """
        route = self.get_route(route_id)
        if not route:
            return False
        
        # 添加防御插件配置
        if 'plugins' not in route:
            route['plugins'] = {}
        
        route['plugins']['cdn-defense'] = plugin_config
        
        return self.set_route(route_id, route)
    
    def disable_defense_plugin(self, route_id: str) -> bool:
        """禁用防御插件"""
        route = self.get_route(route_id)
        if not route:
            return False
        
        if 'plugins' in route and 'cdn-defense' in route['plugins']:
            del route['plugins']['cdn-defense']
        
        return self.set_route(route_id, route)
    
    def update_defense_plugin_config(self, route_id: str, config: Dict) -> bool:
        """更新防御插件配置"""
        plugin_config = {
            'defense_engine_url': config.get('defense_engine_url', 'http://defense-api:5000'),
            'redis_host': config.get('redis_host', 'redis'),
            'redis_port': config.get('redis_port', 6379),
            'tenant_id': config.get('tenant_id'),
            'enable_js_challenge': config.get('enable_js_challenge', True)
        }
        
        return self.enable_defense_plugin(route_id, plugin_config)
    
    # ============ 事件发布 ============
    
    def _publish_config_change(self, event_type: str, tenant_id: str, config: Dict):
        """发布配置变更事件到所有订阅者"""
        event_key = f"/cdn-defense/events/config/{event_type}"
        event_data = {
            'type': event_type,
            'tenant_id': tenant_id,
            'config': config,
            'timestamp': time.time()
        }
        
        try:
            self.etcd.put(event_key, json.dumps(event_data))
        except Exception as e:
            logger.error(f"发布配置事件失败: {e}")
    
    def _publish_route_change(self, event_type: str, route_id: str, route: Dict):
        """发布路由变更事件"""
        event_key = f"/cdn-defense/events/route/{event_type}"
        event_data = {
            'type': event_type,
            'route_id': route_id,
            'route': route,
            'timestamp': time.time()
        }
        
        try:
            self.etcd.put(event_key, json.dumps(event_data))
        except Exception as e:
            logger.error(f"发布路由事件失败: {e}")
    
    def _publish_ssl_change(self, event_type: str, cert_id: str, cert: Dict):
        """发布 SSL 证书变更事件"""
        event_key = f"/cdn-defense/events/ssl/{event_type}"
        event_data = {
            'type': event_type,
            'cert_id': cert_id,
            'cert': cert,
            'timestamp': time.time()
        }
        
        try:
            self.etcd.put(event_key, json.dumps(event_data))
        except Exception as e:
            logger.error(f"发布 SSL 事件失败: {e}")


class NodeSyncManager:
    """节点同步管理器 - 每个节点都同步全局配置"""
    
    def __init__(self, node_id: str, etcd_host='localhost', etcd_port=2379):
        self.node_id = node_id
        self.config_manager = GlobalConfigManager(etcd_host, etcd_port)
        self.local_cache = {}
        self.cache_version = {}
        self.is_syncing = False
    
    def start_sync_daemon(self):
        """
        启动后台同步守护进程
        持续监听全局配置变更
        """
        sync_thread = Thread(target=self._sync_loop, daemon=True)
        sync_thread.start()
        logger.info(f"节点 {self.node_id} 同步守护进程已启动")
    
    def _sync_loop(self):
        """
        同步循环
        监听 etcd 中的所有变更并更新本地缓存
        """
        self.is_syncing = True
        
        def on_config_change(event_type, tenant_id, data):
            logger.info(f"节点 {self.node_id} 收到配置变更: "
                       f"event_type={event_type}, tenant_id={tenant_id}")
            
            if event_type == 'config_update':
                self.local_cache[f"config:{tenant_id}"] = data.get('config')
                self.cache_version[f"config:{tenant_id}"] = data.get('version')
            elif event_type == 'config_delete':
                if f"config:{tenant_id}" in self.local_cache:
                    del self.local_cache[f"config:{tenant_id}"]
        
        try:
            self.config_manager.watch_config_changes(on_config_change)
        except Exception as e:
            logger.error(f"同步循环错误: {e}")
            self.is_syncing = False
    
    def get_local_config(self, tenant_id: str) -> Optional[Dict]:
        """
        从本地缓存获取配置
        如果缓存不存在，从 etcd 同步
        """
        cache_key = f"config:{tenant_id}"
        
        if cache_key in self.local_cache:
            return self.local_cache[cache_key]
        
        # 从 etcd 同步
        config = self.config_manager.get_tenant_config(tenant_id)
        if config:
            self.local_cache[cache_key] = config
        
        return config
    
    def sync_all_configs(self):
        """
        同步所有配置到本地缓存
        """
        configs = self.config_manager.get_all_tenant_configs()
        
        for tenant_id, data in configs.items():
            cache_key = f"config:{tenant_id}"
            self.local_cache[cache_key] = data.get('config')
            self.cache_version[cache_key] = data.get('version')
        
        logger.info(f"节点 {self.node_id} 已同步 {len(configs)} 个配置")
    
    def get_cache_status(self) -> Dict:
        """获取缓存状态"""
        return {
            'node_id': self.node_id,
            'is_syncing': self.is_syncing,
            'cached_items': len(self.local_cache),
            'cache_keys': list(self.local_cache.keys())
        }


class PluginSyncManager:
    """防御插件同步管理器"""
    
    def __init__(self, etcd_host='localhost', etcd_port=2379):
        self.config_manager = GlobalConfigManager(etcd_host, etcd_port)
    
    def apply_defense_to_route(self, route_id: str, tenant_id: str, 
                               defense_config: Dict) -> bool:
        """
        为路由应用防御插件
        自动同步到所有节点和 APISIX
        """
        # 获取或创建路由
        route = self.config_manager.get_route(route_id)
        if not route:
            route = {
                'id': route_id,
                'tenant_id': tenant_id,
                'created_at': time.time()
            }
        
        # 应用防御插件
        plugin_config = {
            'defense_engine_url': defense_config.get('defense_engine_url', 'http://defense-api:5000'),
            'redis_host': defense_config.get('redis_host', 'redis'),
            'redis_port': defense_config.get('redis_port', 6379),
            'tenant_id': tenant_id,
            'enable_js_challenge': defense_config.get('enable_js_challenge', True)
        }
        
        return self.config_manager.enable_defense_plugin(route_id, plugin_config)
    
    def update_all_defense_configs(self, config: Dict) -> int:
        """
        批量更新所有路由的防御配置
        """
        updated_count = 0
        
        # 获取所有路由
        for value, metadata in self.config_manager.etcd.get_prefix('/cdn-defense/routes/'):
            if value:
                data = json.loads(value.decode())
                route = data.get('route', {})
                route_id = route.get('id')
                tenant_id = route.get('tenant_id')
                
                if route_id and tenant_id:
                    if self.apply_defense_to_route(route_id, tenant_id, config):
                        updated_count += 1
        
        logger.info(f"已更新 {updated_count} 个路由的防御配置")
        return updated_count


if __name__ == '__main__':
    import time
    
    # 创建全局配置管理器
    global_mgr = GlobalConfigManager('localhost', 2379)
    
    # 创建节点同步管理器
    node_mgr = NodeSyncManager('node-1', 'localhost', 2379)
    node_mgr.start_sync_daemon()
    
    # 设置全局配置
    global_mgr.set_tenant_config('tenant-001', {
        'rate_limit_per_minute': 100,
        'js_challenge_threshold': 30,
        'block_threshold': 70
    })
    
    # 设置路由
    global_mgr.set_route('api-route-1', {
        'id': 'api-route-1',
        'tenant_id': 'tenant-001',
        'uri': '/api/*',
        'methods': ['GET', 'POST'],
        'plugins': {}
    })
    
    # 应用防御插件
    global_mgr.enable_defense_plugin('api-route-1', {
        'defense_engine_url': 'http://defense-api:5000',
        'redis_host': 'redis',
        'redis_port': 6379,
        'tenant_id': 'tenant-001',
        'enable_js_challenge': True
    })
    
    # 等待同步
    time.sleep(2)
    
    # 验证本地同步
    config = node_mgr.get_local_config('tenant-001')
    print(f"本地缓存配置: {config}")
    print(f"缓存状态: {node_mgr.get_cache_status()}")
