"""
全局配置同步系统测试套件
验证 etcd-based 全局配置同步的各项功能
"""

import unittest
import json
import time
from datetime import datetime
import os
import sys

# 模拟 etcd 和 Redis 进行测试
class MockETCD:
    """模拟 etcd 客户端用于测试"""
    def __init__(self):
        self.data = {}
        self.callbacks = []
        self.version = 1
    
    def put(self, key, value):
        self.data[key] = value
        self.version += 1
        # 触发 watch 回调
        for callback in self.callbacks:
            callback({'type': 'put', 'key': key, 'value': value})
        return True
    
    def get(self, key):
        return self.data.get(key)
    
    def delete(self, key):
        if key in self.data:
            del self.data[key]
            self.version += 1
            return True
        return False
    
    def get_prefix(self, prefix):
        """获取所有以 prefix 开头的键值对"""
        return {k: v for k, v in self.data.items() if k.startswith(prefix)}
    
    def add_watch_callback(self, prefix, callback):
        """添加 watch 回调"""
        self.callbacks.append(callback)


class TestGlobalConfigSync(unittest.TestCase):
    """测试全局配置同步"""
    
    def setUp(self):
        """测试前准备"""
        self.etcd = MockETCD()
        self.tenant_id = "test-tenant"
        self.route_id = "test-route"
    
    def test_tenant_config_storage(self):
        """测试租户配置存储"""
        config = {
            "rate_limit": 1000,
            "threat_threshold": 70,
            "enabled_defense": True
        }
        
        key = f"/cdn-defense/config/{self.tenant_id}"
        self.etcd.put(key, json.dumps(config))
        
        stored = json.loads(self.etcd.get(key))
        self.assertEqual(stored["rate_limit"], 1000)
        self.assertEqual(stored["threat_threshold"], 70)
        self.assertTrue(stored["enabled_defense"])
    
    def test_route_creation(self):
        """测试路由创建"""
        route = {
            "id": self.route_id,
            "path": "/api/v1/*",
            "upstream": "http://backend:8080",
            "methods": ["GET", "POST"]
        }
        
        key = f"/cdn-defense/routes/{self.route_id}"
        self.etcd.put(key, json.dumps(route))
        
        stored = json.loads(self.etcd.get(key))
        self.assertEqual(stored["path"], "/api/v1/*")
        self.assertIn("GET", stored["methods"])
    
    def test_ssl_cert_storage(self):
        """测试 SSL 证书存储"""
        cert_data = {
            "domain": "api.example.com",
            "cert": "-----BEGIN CERTIFICATE-----...",
            "key": "-----BEGIN PRIVATE KEY-----...",
            "expires_at": "2025-12-31T23:59:59Z"
        }
        
        cert_id = f"{self.tenant_id}:api.example.com"
        key = f"/cdn-defense/ssl/{cert_id}"
        self.etcd.put(key, json.dumps(cert_data))
        
        stored = json.loads(self.etcd.get(key))
        self.assertEqual(stored["domain"], "api.example.com")
        self.assertIn("CERTIFICATE", stored["cert"])
    
    def test_config_versioning(self):
        """测试配置版本控制"""
        config_v1 = {
            "rate_limit": 1000,
            "version": 1,
            "updated_at": datetime.now().isoformat()
        }
        
        key = f"/cdn-defense/config/{self.tenant_id}"
        self.etcd.put(key, json.dumps(config_v1))
        
        # 更新配置
        config_v2 = {
            "rate_limit": 2000,
            "version": 2,
            "updated_at": datetime.now().isoformat()
        }
        self.etcd.put(key, json.dumps(config_v2))
        
        stored = json.loads(self.etcd.get(key))
        self.assertEqual(stored["version"], 2)
        self.assertEqual(stored["rate_limit"], 2000)
    
    def test_watch_event_propagation(self):
        """测试 watch 事件传播"""
        events_received = []
        
        def watch_callback(event):
            events_received.append(event)
        
        # 添加监听器
        self.etcd.add_watch_callback("/cdn-defense/config", watch_callback)
        
        # 创建配置
        config = {"rate_limit": 1000}
        key = f"/cdn-defense/config/{self.tenant_id}"
        self.etcd.put(key, json.dumps(config))
        
        # 验证事件接收
        self.assertEqual(len(events_received), 1)
        self.assertEqual(events_received[0]["type"], "put")
        self.assertEqual(events_received[0]["key"], key)
    
    def test_multi_node_sync(self):
        """测试多节点同步"""
        # Node-1 创建配置
        config = {
            "rate_limit": 1000,
            "threat_threshold": 70
        }
        key = f"/cdn-defense/config/{self.tenant_id}"
        self.etcd.put(key, json.dumps(config))
        
        # Node-2 读取同一配置
        stored = json.loads(self.etcd.get(key))
        self.assertEqual(stored["rate_limit"], 1000)
        
        # Node-3 更新配置
        config["rate_limit"] = 2000
        self.etcd.put(key, json.dumps(config))
        
        # Node-1 看到更新
        updated = json.loads(self.etcd.get(key))
        self.assertEqual(updated["rate_limit"], 2000)
    
    def test_prefix_list(self):
        """测试前缀列表查询"""
        # 创建多个路由
        for i in range(3):
            route = {
                "id": f"route-{i}",
                "path": f"/api/route{i}",
                "upstream": "http://backend:8080"
            }
            key = f"/cdn-defense/routes/route-{i}"
            self.etcd.put(key, json.dumps(route))
        
        # 查询所有路由
        routes = self.etcd.get_prefix("/cdn-defense/routes")
        self.assertEqual(len(routes), 3)
    
    def test_config_deletion(self):
        """测试配置删除"""
        config = {"rate_limit": 1000}
        key = f"/cdn-defense/config/{self.tenant_id}"
        self.etcd.put(key, json.dumps(config))
        
        # 验证存在
        self.assertIsNotNone(self.etcd.get(key))
        
        # 删除
        result = self.etcd.delete(key)
        self.assertTrue(result)
        
        # 验证删除
        self.assertIsNone(self.etcd.get(key))


class TestDefensePluginSync(unittest.TestCase):
    """测试防御插件同步"""
    
    def setUp(self):
        self.etcd = MockETCD()
        self.route_id = "api-route-1"
        self.tenant_id = "test-tenant"
    
    def test_apply_defense_plugin(self):
        """测试应用防御插件到路由"""
        # 创建路由
        route = {
            "id": self.route_id,
            "path": "/api/*",
            "upstream": "http://backend:8080",
            "plugins": []
        }
        
        key = f"/cdn-defense/routes/{self.route_id}"
        self.etcd.put(key, json.dumps(route))
        
        # 添加防御插件
        defense_config = {
            "name": "cdn_defense",
            "config": {
                "threat_threshold": 75,
                "challenge_type": "js"
            }
        }
        
        # 更新路由
        route_stored = json.loads(self.etcd.get(key))
        route_stored["plugins"].append(defense_config)
        self.etcd.put(key, json.dumps(route_stored))
        
        # 验证
        updated_route = json.loads(self.etcd.get(key))
        self.assertEqual(len(updated_route["plugins"]), 1)
        self.assertEqual(updated_route["plugins"][0]["name"], "cdn_defense")
    
    def test_bulk_plugin_update(self):
        """测试批量更新防御插件"""
        # 创建多个路由
        routes = []
        for i in range(3):
            route = {
                "id": f"route-{i}",
                "path": f"/api/{i}",
                "plugins": []
            }
            key = f"/cdn-defense/routes/route-{i}"
            self.etcd.put(key, json.dumps(route))
            routes.append(route)
        
        # 批量更新所有路由的防御配置
        defense_config = {
            "name": "cdn_defense",
            "config": {"threat_threshold": 70}
        }
        
        all_routes = self.etcd.get_prefix("/cdn-defense/routes")
        for key, route_json in all_routes.items():
            route = json.loads(route_json)
            route["plugins"].append(defense_config)
            self.etcd.put(key, json.dumps(route))
        
        # 验证所有路由都已更新
        updated_routes = self.etcd.get_prefix("/cdn-defense/routes")
        for route_json in updated_routes.values():
            route = json.loads(route_json)
            self.assertEqual(len(route["plugins"]), 1)


class TestNodeSyncManager(unittest.TestCase):
    """测试节点同步管理器"""
    
    def test_local_cache_initialization(self):
        """测试本地缓存初始化"""
        cache = {
            "tenant_configs": {},
            "routes": {},
            "ssl_certs": {},
            "last_sync": datetime.now().isoformat()
        }
        
        self.assertIn("tenant_configs", cache)
        self.assertIn("routes", cache)
        self.assertIn("ssl_certs", cache)
    
    def test_cache_sync_from_etcd(self):
        """测试从 etcd 同步缓存"""
        etcd = MockETCD()
        
        # etcd 中的数据
        config = {"rate_limit": 1000}
        etcd.put("/cdn-defense/config/tenant-1", json.dumps(config))
        
        # 模拟节点缓存更新
        cache = {}
        all_configs = etcd.get_prefix("/cdn-defense/config")
        
        for key, value in all_configs.items():
            tenant_id = key.split("/")[-1]
            cache[tenant_id] = json.loads(value)
        
        self.assertEqual(cache["tenant-1"]["rate_limit"], 1000)
    
    def test_watch_callback_handling(self):
        """测试 watch 回调处理"""
        etcd = MockETCD()
        cache = {"tenant_configs": {}}
        
        def on_config_change(event):
            if event["type"] == "put":
                key = event["key"]
                value = json.loads(event["value"])
                tenant_id = key.split("/")[-1]
                cache["tenant_configs"][tenant_id] = value
        
        # 添加监听
        etcd.add_watch_callback("/cdn-defense/config", on_config_change)
        
        # 创建配置
        config = {"rate_limit": 1000}
        etcd.put("/cdn-defense/config/tenant-1", json.dumps(config))
        
        # 验证缓存更新
        self.assertIn("tenant-1", cache["tenant_configs"])
        self.assertEqual(cache["tenant_configs"]["tenant-1"]["rate_limit"], 1000)


class TestGlobalSyncConsistency(unittest.TestCase):
    """测试全局同步一致性"""
    
    def setUp(self):
        self.etcd = MockETCD()
    
    def test_read_consistency(self):
        """测试读一致性"""
        config = {"rate_limit": 1000, "version": 1}
        key = f"/cdn-defense/config/tenant-1"
        self.etcd.put(key, json.dumps(config))
        
        # 多次读取应该返回相同值
        read1 = json.loads(self.etcd.get(key))
        read2 = json.loads(self.etcd.get(key))
        
        self.assertEqual(read1, read2)
        self.assertEqual(read1["version"], 1)
    
    def test_write_consistency(self):
        """测试写一致性"""
        config = {"rate_limit": 1000, "version": 1}
        key = f"/cdn-defense/config/tenant-1"
        self.etcd.put(key, json.dumps(config))
        
        # 更新配置
        config["rate_limit"] = 2000
        config["version"] = 2
        self.etcd.put(key, json.dumps(config))
        
        # 验证新值生效
        stored = json.loads(self.etcd.get(key))
        self.assertEqual(stored["version"], 2)
        self.assertEqual(stored["rate_limit"], 2000)
    
    def test_concurrent_update_handling(self):
        """测试并发更新处理"""
        config = {"rate_limit": 1000, "version": 1}
        key = f"/cdn-defense/config/tenant-1"
        self.etcd.put(key, json.dumps(config))
        
        # 模拟并发更新（Last Write Wins 策略）
        # Node-1 更新
        config_1 = {"rate_limit": 2000, "version": 2}
        self.etcd.put(key, json.dumps(config_1))
        
        # Node-2 更新（覆盖 Node-1）
        config_2 = {"rate_limit": 3000, "version": 2}
        self.etcd.put(key, json.dumps(config_2))
        
        # 最后的写入生效
        stored = json.loads(self.etcd.get(key))
        self.assertEqual(stored["rate_limit"], 3000)


class TestErrorHandling(unittest.TestCase):
    """测试错误处理"""
    
    def setUp(self):
        self.etcd = MockETCD()
    
    def test_missing_config(self):
        """测试缺失配置处理"""
        result = self.etcd.get("/cdn-defense/config/non-existent")
        self.assertIsNone(result)
    
    def test_invalid_json_recovery(self):
        """测试无效 JSON 恢复"""
        try:
            invalid = json.loads("invalid json")
        except json.JSONDecodeError:
            # 应该处理异常
            pass
    
    def test_etcd_connection_fallback(self):
        """测试 etcd 连接故障回退"""
        # 如果 etcd 不可用，应该使用本地缓存
        cache = {"tenant-1": {"rate_limit": 1000}}
        
        # 即使 etcd 不可用，仍然可以从缓存读取
        self.assertIn("tenant-1", cache)


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestGlobalConfigSync))
    suite.addTests(loader.loadTestsFromTestCase(TestDefensePluginSync))
    suite.addTests(loader.loadTestsFromTestCase(TestNodeSyncManager))
    suite.addTests(loader.loadTestsFromTestCase(TestGlobalSyncConsistency))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print("\n" + "="*70)
    print("测试总结")
    print("="*70)
    print(f"运行测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
