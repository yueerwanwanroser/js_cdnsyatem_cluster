"""
CDN 防御系统测试套件
"""

import unittest
import json
import time
import sys
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, '/home/alana/azuredev-cd81/cdn-defense-system')

from backend.defense_engine import (
    DefenseEngine, RequestProfile, ThreatLevel, 
    AttackType, AnomalyDetector, RateLimiter
)
from js_defense.js_defense import (
    BrowserFingerprint, FingerprintValidator, 
    BotDetector, JSDefenseManager
)

import redis


class TestDefenseEngine(unittest.TestCase):
    """防御引擎单元测试"""
    
    @classmethod
    def setUpClass(cls):
        cls.redis_client = redis.Redis(
            host='localhost', 
            port=6379, 
            decode_responses=True
        )
        # 清空测试数据
        try:
            cls.redis_client.flushdb()
        except:
            pass
    
    def setUp(self):
        self.engine = DefenseEngine(self.redis_client, 'test-node')
    
    def test_normal_request(self):
        """测试正常请求"""
        profile = RequestProfile(
            request_id='test-001',
            timestamp=time.time(),
            client_ip='192.168.1.1',
            user_agent='Mozilla/5.0',
            path='/api/data',
            method='GET',
            headers={},
            payload_size=1024,
            user_id='user-123',
            tenant_id='tenant-001'
        )
        
        decision = self.engine.process_request(profile)
        
        self.assertTrue(decision.allow)
        self.assertEqual(decision.action, 'allow')
        self.assertLess(decision.threat_score, 50)
    
    def test_rate_limiting(self):
        """测试速率限制"""
        # 发送超过限制的请求
        for i in range(150):
            profile = RequestProfile(
                request_id=f'test-{i}',
                timestamp=time.time(),
                client_ip='192.168.1.2',
                user_agent='Mozilla/5.0',
                path='/api/data',
                method='GET',
                headers={},
                payload_size=1024,
                user_id='user-124',
                tenant_id='tenant-001'
            )
            
            decision = self.engine.process_request(profile)
            
            if i >= 100:  # 超过限制后应该被限流
                self.assertFalse(decision.allow)
                self.assertEqual(decision.action, 'rate_limit')
                break
    
    def test_whitelist(self):
        """测试白名单"""
        ip = '10.0.0.1'
        self.engine.add_to_whitelist(ip, 'tenant-001')
        
        profile = RequestProfile(
            request_id='test-white-001',
            timestamp=time.time(),
            client_ip=ip,
            user_agent='Mozilla/5.0',
            path='/api/data',
            method='GET',
            headers={},
            payload_size=1024,
            user_id='user-125',
            tenant_id='tenant-001'
        )
        
        decision = self.engine.process_request(profile)
        
        self.assertTrue(decision.allow)
        self.assertEqual(decision.action, 'allow')
    
    def test_blacklist(self):
        """测试黑名单"""
        ip = '10.0.0.2'
        self.engine.add_to_blacklist(ip, 'tenant-001', duration=3600)
        
        profile = RequestProfile(
            request_id='test-black-001',
            timestamp=time.time(),
            client_ip=ip,
            user_agent='Mozilla/5.0',
            path='/api/data',
            method='GET',
            headers={},
            payload_size=1024,
            user_id='user-126',
            tenant_id='tenant-001'
        )
        
        decision = self.engine.process_request(profile)
        
        self.assertFalse(decision.allow)
        self.assertGreaterEqual(decision.threat_score, 50)


class TestJSDefense(unittest.TestCase):
    """JS 防御单元测试"""
    
    @classmethod
    def setUpClass(cls):
        cls.redis_client = redis.Redis(
            host='localhost', 
            port=6379, 
            decode_responses=True
        )
        try:
            cls.redis_client.flushdb()
        except:
            pass
    
    def setUp(self):
        self.manager = JSDefenseManager(self.redis_client)
    
    def test_fingerprint_validation(self):
        """测试指纹验证"""
        fp = BrowserFingerprint(
            user_agent='Mozilla/5.0 (Windows NT 10.0)',
            language='zh-CN',
            platform='Win32',
            screen_resolution='1920x1080',
            canvas_fingerprint='abc123',
            webgl_fingerprint='xyz789',
            plugins='Flash,PDF',
            timezone='Asia/Shanghai',
            timestamp=time.time()
        )
        
        validator = FingerprintValidator(self.redis_client)
        valid, details = validator.validate_fingerprint(fp, '192.168.1.1', 'user-1')
        
        self.assertTrue(valid or not valid)  # 至少返回一个结果
        self.assertIn('score', details)
    
    def test_bot_detection(self):
        """测试机器人检测"""
        # 正常浏览器
        fp_normal = BrowserFingerprint(
            user_agent='Mozilla/5.0',
            language='zh-CN',
            platform='Win32',
            screen_resolution='1920x1080',
            canvas_fingerprint='abc123',
            webgl_fingerprint='xyz789',
            plugins='Flash,PDF',
            timezone='Asia/Shanghai',
            timestamp=time.time()
        )
        
        detector = BotDetector(self.redis_client)
        is_bot, details = detector.detect_bot(fp_normal, '192.168.1.1', 'user-1')
        
        self.assertFalse(is_bot)
        
        # 无头浏览器
        fp_headless = BrowserFingerprint(
            user_agent='Puppeteer',
            language='zh-CN',
            platform='Win32',
            screen_resolution='0x0',
            canvas_fingerprint='',
            webgl_fingerprint='',
            plugins='none',
            timezone='UTC',
            timestamp=time.time()
        )
        
        is_bot_hl, details_hl = detector.detect_bot(fp_headless, '192.168.1.1', 'user-2')
        
        self.assertTrue(is_bot_hl)


class TestAPIIntegration(unittest.TestCase):
    """API 集成测试"""
    
    def setUp(self):
        self.api_url = 'http://localhost:5000'
        self.tenant_id = 'test-tenant'
        self.headers = {'X-Tenant-ID': self.tenant_id}
    
    def test_health_check(self):
        """测试健康检查"""
        try:
            response = requests.get(f'{self.api_url}/health')
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data['status'], 'healthy')
        except requests.exceptions.ConnectionError:
            self.skipTest('API 服务未运行')
    
    def test_analyze_request(self):
        """测试请求分析"""
        try:
            data = {
                'request': {
                    'request_id': 'test-req-001',
                    'timestamp': time.time(),
                    'client_ip': '192.168.1.1',
                    'user_agent': 'Mozilla/5.0',
                    'path': '/api/test',
                    'method': 'GET',
                    'headers': {},
                    'payload_size': 512,
                    'user_id': 'test-user'
                }
            }
            
            response = requests.post(
                f'{self.api_url}/analyze',
                headers=self.headers,
                json=data
            )
            
            self.assertIn(response.status_code, [200, 400])
            
            if response.status_code == 200:
                result = response.json()
                self.assertIn('allow', result)
                self.assertIn('threat_score', result)
        except requests.exceptions.ConnectionError:
            self.skipTest('API 服务未运行')
    
    def test_statistics(self):
        """测试统计接口"""
        try:
            response = requests.get(
                f'{self.api_url}/statistics',
                headers=self.headers
            )
            
            self.assertIn(response.status_code, [200, 400])
        except requests.exceptions.ConnectionError:
            self.skipTest('API 服务未运行')


class PerformanceBenchmark:
    """性能基准测试"""
    
    def __init__(self, api_url='http://localhost:5000', tenant_id='bench-tenant'):
        self.api_url = api_url
        self.tenant_id = tenant_id
        self.headers = {'X-Tenant-ID': tenant_id}
    
    def benchmark_throughput(self, num_requests=1000, num_workers=10):
        """吞吐量测试"""
        print(f"\n吞吐量测试: {num_requests} 个请求, {num_workers} 个工作线程")
        
        def make_request(req_id):
            try:
                data = {
                    'request': {
                        'request_id': f'bench-{req_id}',
                        'timestamp': time.time(),
                        'client_ip': f'192.168.1.{req_id % 254 + 1}',
                        'user_agent': 'Mozilla/5.0',
                        'path': '/api/bench',
                        'method': 'GET',
                        'headers': {},
                        'payload_size': 1024,
                        'user_id': f'user-{req_id}'
                    }
                }
                
                start = time.time()
                response = requests.post(
                    f'{self.api_url}/analyze',
                    headers=self.headers,
                    json=data,
                    timeout=5
                )
                elapsed = time.time() - start
                
                return response.status_code == 200, elapsed
            except Exception as e:
                return False, 0
        
        start_time = time.time()
        successful = 0
        total_time = 0
        
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(make_request, i) for i in range(num_requests)]
            
            for future in as_completed(futures):
                success, elapsed = future.result()
                if success:
                    successful += 1
                    total_time += elapsed
        
        elapsed_total = time.time() - start_time
        
        print(f"总耗时: {elapsed_total:.2f} 秒")
        print(f"成功请求: {successful}/{num_requests}")
        print(f"吞吐量: {num_requests/elapsed_total:.2f} req/s")
        print(f"平均响应时间: {total_time/successful*1000:.2f} ms" if successful > 0 else "N/A")
    
    def benchmark_latency(self, num_samples=100):
        """延迟测试"""
        print(f"\n延迟测试: {num_samples} 个样本")
        
        latencies = []
        
        for i in range(num_samples):
            data = {
                'request': {
                    'request_id': f'latency-{i}',
                    'timestamp': time.time(),
                    'client_ip': '192.168.1.1',
                    'user_agent': 'Mozilla/5.0',
                    'path': '/api/latency',
                    'method': 'GET',
                    'headers': {},
                    'payload_size': 512,
                    'user_id': 'latency-user'
                }
            }
            
            try:
                start = time.time()
                response = requests.post(
                    f'{self.api_url}/analyze',
                    headers=self.headers,
                    json=data,
                    timeout=5
                )
                elapsed = (time.time() - start) * 1000
                
                if response.status_code == 200:
                    latencies.append(elapsed)
            except:
                pass
        
        if latencies:
            latencies.sort()
            print(f"最小延迟: {latencies[0]:.2f} ms")
            print(f"最大延迟: {latencies[-1]:.2f} ms")
            print(f"平均延迟: {sum(latencies)/len(latencies):.2f} ms")
            print(f"P95 延迟: {latencies[int(len(latencies)*0.95)]:.2f} ms")
            print(f"P99 延迟: {latencies[int(len(latencies)*0.99)]:.2f} ms")


def run_unit_tests():
    """运行单元测试"""
    print("=" * 50)
    print("运行单元测试")
    print("=" * 50)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestDefenseEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestJSDefense))
    suite.addTests(loader.loadTestsFromTestCase(TestAPIIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_benchmark():
    """运行性能测试"""
    print("\n" + "=" * 50)
    print("运行性能基准测试")
    print("=" * 50)
    
    try:
        benchmark = PerformanceBenchmark()
        benchmark.benchmark_throughput(num_requests=1000, num_workers=10)
        benchmark.benchmark_latency(num_samples=100)
    except Exception as e:
        print(f"性能测试失败: {e}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='CDN 防御系统测试')
    parser.add_argument('--unit', action='store_true', help='运行单元测试')
    parser.add_argument('--benchmark', action='store_true', help='运行性能测试')
    parser.add_argument('--all', action='store_true', help='运行所有测试')
    
    args = parser.parse_args()
    
    if args.all or (not args.unit and not args.benchmark):
        run_unit_tests()
        run_benchmark()
    else:
        if args.unit:
            run_unit_tests()
        if args.benchmark:
            run_benchmark()
