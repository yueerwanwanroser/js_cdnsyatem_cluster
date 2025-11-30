"""
JS 防御模块 - 浏览器指纹识别、验证码生成、反爬虫
"""

import hashlib
import json
import time
import base64
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import redis


@dataclass
class BrowserFingerprint:
    """浏览器指纹"""
    user_agent: str
    language: str
    platform: str
    screen_resolution: str
    timezone: str
    canvas_fingerprint: str
    webgl_fingerprint: str
    plugins: str
    timestamp: float
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'user_agent': self.user_agent,
            'language': self.language,
            'platform': self.platform,
            'screen_resolution': self.screen_resolution,
            'timezone': self.timezone,
            'canvas_fingerprint': self.canvas_fingerprint,
            'webgl_fingerprint': self.webgl_fingerprint,
            'plugins': self.plugins,
            'timestamp': self.timestamp
        }
    
    def to_hash(self) -> str:
        """生成指纹哈希"""
        data = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()


class FingerprintValidator:
    """浏览器指纹验证器"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def validate_fingerprint(self, fingerprint: BrowserFingerprint, 
                            client_ip: str, user_id: str) -> Tuple[bool, Dict]:
        """
        验证浏览器指纹
        :return: (是否通过, 详情)
        """
        result = {
            'valid': True,
            'score': 100.0,
            'warnings': []
        }
        
        # 1. 检查用户代理一致性
        key = f"ua_cache:{client_ip}:{user_id}"
        cached_ua = self.redis.get(key)
        
        if cached_ua and cached_ua != fingerprint.user_agent:
            result['score'] -= 20
            result['warnings'].append('用户代理不一致')
        else:
            self.redis.setex(key, 3600, fingerprint.user_agent)
        
        # 2. 检查指纹一致性
        fingerprint_hash = fingerprint.to_hash()
        key = f"fingerprint_cache:{client_ip}:{user_id}"
        cached_fingerprint = self.redis.get(key)
        
        if cached_fingerprint and cached_fingerprint != fingerprint_hash:
            result['score'] -= 15
            result['warnings'].append('设备指纹不一致')
        else:
            self.redis.setex(key, 3600, fingerprint_hash)
        
        # 3. 检查时间戳异常
        current_time = time.time()
        time_diff = abs(current_time - fingerprint.timestamp)
        
        if time_diff > 10:  # 超过 10 秒
            result['score'] -= 10
            result['warnings'].append('时间戳异常')
        
        # 4. 检查屏幕分辨率
        if fingerprint.screen_resolution in ['0x0', '1x1']:
            result['score'] -= 25
            result['warnings'].append('屏幕分辨率异常 (可能是无头浏览器)')
        
        # 5. 检查 Canvas 指纹（反爬虫指标）
        if not fingerprint.canvas_fingerprint or fingerprint.canvas_fingerprint == '':
            result['score'] -= 30
            result['warnings'].append('Canvas 指纹缺失 (可能是机器人)')
        
        # 6. 检查 WebGL 指纹
        if not fingerprint.webgl_fingerprint or fingerprint.webgl_fingerprint == '':
            result['score'] -= 20
            result['warnings'].append('WebGL 指纹缺失')
        
        # 7. 检查插件信息
        if fingerprint.plugins and fingerprint.plugins != 'unknown':
            # 正常浏览器应该有插件信息
            pass
        else:
            result['score'] -= 15
            result['warnings'].append('插件信息缺失')
        
        # 计算最终判定
        result['valid'] = result['score'] >= 60
        result['fingerprint_hash'] = fingerprint_hash
        
        return result['valid'], result


class ChallengeGenerator:
    """验证码生成器"""
    
    @staticmethod
    def generate_math_challenge() -> Dict:
        """生成数学挑战"""
        import random
        
        num1 = random.randint(1, 100)
        num2 = random.randint(1, 100)
        op = random.choice(['+', '-', '*'])
        
        if op == '+':
            answer = num1 + num2
        elif op == '-':
            answer = num1 - num2
        else:
            answer = num1 * num2
        
        # 生成验证码
        answer_hash = hashlib.sha256(
            (str(answer) + str(time.time())).encode()
        ).hexdigest()
        
        return {
            'type': 'math',
            'question': f'{num1} {op} {num2} = ?',
            'answer_hash': answer_hash,
            'expires_at': time.time() + 300  # 5 分钟有效期
        }
    
    @staticmethod
    def generate_puzzle_challenge() -> Dict:
        """生成拼图挑战"""
        import random
        
        puzzle_id = hashlib.md5(
            str(time.time()).encode()
        ).hexdigest()[:8]
        
        return {
            'type': 'puzzle',
            'puzzle_id': puzzle_id,
            'background': f'/api/puzzle/{puzzle_id}/bg',
            'slider': f'/api/puzzle/{puzzle_id}/slider',
            'expires_at': time.time() + 300
        }
    
    @staticmethod
    def generate_behavior_challenge() -> Dict:
        """生成行为验证码"""
        import random
        
        challenge_id = hashlib.md5(
            str(time.time()).encode()
        ).hexdigest()
        
        # 记录设备动作
        actions = [
            'move_mouse',
            'click_button',
            'scroll_page',
            'type_text'
        ]
        
        required_actions = random.sample(actions, random.randint(1, 3))
        
        return {
            'type': 'behavior',
            'challenge_id': challenge_id,
            'required_actions': required_actions,
            'expires_at': time.time() + 300
        }


class BotDetector:
    """机器人检测器"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def detect_bot(self, fingerprint: BrowserFingerprint, 
                   client_ip: str, user_id: str) -> Tuple[bool, Dict]:
        """
        检测是否为机器人
        :return: (是否是机器人, 检测详情)
        """
        score = 0.0
        indicators = {}
        
        # 1. Canvas 指纹检测
        if not fingerprint.canvas_fingerprint or len(fingerprint.canvas_fingerprint) < 20:
            score += 25
            indicators['canvas_missing'] = True
        
        # 2. WebGL 检测
        if not fingerprint.webgl_fingerprint:
            score += 20
            indicators['webgl_missing'] = True
        
        # 3. 无头浏览器检测（通过用户代理）
        headless_keywords = ['headless', 'phantom', 'zombie', 'puppeteer', 'jsdom']
        if any(keyword in fingerprint.user_agent.lower() for keyword in headless_keywords):
            score += 30
            indicators['headless_detected'] = True
        
        # 4. 屏幕分辨率异常
        if fingerprint.screen_resolution in ['0x0', '1x1', 'unknown']:
            score += 25
            indicators['invalid_screen_resolution'] = True
        
        # 5. 速度异常（检查请求频率）
        key = f"bot_detection:{client_ip}:{user_id}:timestamps"
        timestamps = self.redis.lrange(key, -5, -1)
        
        if len(timestamps) >= 5:
            recent_timestamps = [float(ts) for ts in timestamps]
            time_diffs = [recent_timestamps[i+1] - recent_timestamps[i] 
                         for i in range(len(recent_timestamps)-1)]
            avg_diff = sum(time_diffs) / len(time_diffs)
            
            if avg_diff < 0.05:  # 平均间隔小于 50ms
                score += 20
                indicators['rapid_requests'] = True
        
        # 记录当前时间戳
        self.redis.lpush(key, time.time())
        self.redis.ltrim(key, -10, -1)
        self.redis.expire(key, 3600)
        
        # 6. 插件信息检测
        if fingerprint.plugins == 'none' or fingerprint.plugins == '':
            score += 15
            indicators['no_plugins'] = True
        
        # 7. 时间同步检测
        if fingerprint.timestamp and abs(time.time() - fingerprint.timestamp) > 60:
            score += 10
            indicators['timestamp_anomaly'] = True
        
        is_bot = score >= 50
        
        return is_bot, {
            'is_bot': is_bot,
            'bot_score': score,
            'indicators': indicators,
            'recommendation': 'block' if is_bot else 'allow'
        }


class DeviceTrustManager:
    """设备信任管理"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def trust_device(self, fingerprint: BrowserFingerprint, 
                     client_ip: str, user_id: str, duration: int = 2592000):
        """
        信任设备（30 天）
        """
        device_key = f"trusted_device:{user_id}:{fingerprint.to_hash()}"
        device_info = {
            'ip': client_ip,
            'fingerprint': fingerprint.to_hash(),
            'user_agent': fingerprint.user_agent,
            'trusted_at': time.time(),
            'last_seen': time.time()
        }
        
        self.redis.setex(
            device_key,
            duration,
            json.dumps(device_info)
        )
    
    def is_trusted_device(self, fingerprint: BrowserFingerprint, 
                         user_id: str) -> bool:
        """
        检查是否是信任的设备
        """
        device_key = f"trusted_device:{user_id}:{fingerprint.to_hash()}"
        return self.redis.exists(device_key) > 0
    
    def get_trusted_devices(self, user_id: str) -> list:
        """
        获取用户的所有信任设备
        """
        pattern = f"trusted_device:{user_id}:*"
        keys = self.redis.keys(pattern)
        
        devices = []
        for key in keys:
            device_data = self.redis.get(key)
            if device_data:
                devices.append(json.loads(device_data))
        
        return devices
    
    def revoke_device(self, user_id: str, fingerprint_hash: str):
        """
        撤销设备信任
        """
        device_key = f"trusted_device:{user_id}:{fingerprint_hash}"
        self.redis.delete(device_key)


class JSDefenseManager:
    """JS 防御管理器"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.validator = FingerprintValidator(redis_client)
        self.bot_detector = BotDetector(redis_client)
        self.device_trust = DeviceTrustManager(redis_client)
    
    def create_js_challenge(self, client_ip: str, user_id: str, 
                            tenant_id: str) -> Dict:
        """创建 JS 挑战"""
        challenge_id = hashlib.md5(
            f"{client_ip}{user_id}{time.time()}".encode()
        ).hexdigest()
        
        challenge = {
            'id': challenge_id,
            'type': 'fingerprint',
            'created_at': time.time(),
            'expires_at': time.time() + 300,
            'client_ip': client_ip,
            'user_id': user_id,
            'tenant_id': tenant_id
        }
        
        # 保存到 Redis
        key = f"js_challenge:{challenge_id}"
        self.redis.setex(key, 300, json.dumps(challenge))
        
        return challenge
    
    def verify_js_response(self, challenge_id: str, response: Dict) -> Tuple[bool, Dict]:
        """验证 JS 响应"""
        key = f"js_challenge:{challenge_id}"
        challenge_data = self.redis.get(key)
        
        if not challenge_data:
            return False, {'reason': '挑战已过期'}
        
        challenge = json.loads(challenge_data)
        
        # 验证时间戳
        if time.time() > challenge['expires_at']:
            self.redis.delete(key)
            return False, {'reason': '挑战已过期'}
        
        # 提取指纹
        fingerprint_data = response.get('fingerprint', {})
        fingerprint = BrowserFingerprint(
            user_agent=fingerprint_data.get('ua', ''),
            language=fingerprint_data.get('lang', ''),
            platform=fingerprint_data.get('platform', ''),
            screen_resolution=fingerprint_data.get('screen', ''),
            timezone=fingerprint_data.get('timezone', ''),
            canvas_fingerprint=fingerprint_data.get('canvas', ''),
            webgl_fingerprint=fingerprint_data.get('webgl', ''),
            plugins=fingerprint_data.get('plugins', ''),
            timestamp=fingerprint_data.get('time', time.time())
        )
        
        # 验证指纹
        fingerprint_valid, fp_details = self.validator.validate_fingerprint(
            fingerprint,
            challenge['client_ip'],
            challenge['user_id']
        )
        
        # 检测机器人
        is_bot, bot_details = self.bot_detector.detect_bot(
            fingerprint,
            challenge['client_ip'],
            challenge['user_id']
        )
        
        if is_bot:
            return False, {'reason': '检测到机器人行为', 'details': bot_details}
        
        if fingerprint_valid:
            # 信任设备（可选）
            self.device_trust.trust_device(
                fingerprint,
                challenge['client_ip'],
                challenge['user_id']
            )
        
        self.redis.delete(key)
        
        return fingerprint_valid, {
            'fingerprint_valid': fingerprint_valid,
            'fingerprint_score': fp_details.get('score'),
            'bot_score': bot_details.get('bot_score')
        }


if __name__ == '__main__':
    # 测试
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    # 创建指纹
    fp = BrowserFingerprint(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        language='zh-CN',
        platform='Win32',
        screen_resolution='1920x1080',
        timezone='Asia/Shanghai',
        canvas_fingerprint='abc123def456',
        webgl_fingerprint='xyz789',
        plugins='Flash,PDF',
        timestamp=time.time()
    )
    
    # 创建管理器
    manager = JSDefenseManager(redis_client)
    
    # 创建挑战
    challenge = manager.create_js_challenge('192.168.1.1', 'user-123', 'tenant-001')
    print(f"挑战创建: {challenge}")
    
    # 验证响应
    response = {
        'fingerprint': {
            'ua': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'lang': 'zh-CN',
            'platform': 'Win32',
            'screen': '1920x1080',
            'timezone': 'Asia/Shanghai',
            'canvas': 'abc123def456',
            'webgl': 'xyz789',
            'time': time.time()
        }
    }
    
    valid, details = manager.verify_js_response(challenge['id'], response)
    print(f"验证结果: {valid}, 详情: {details}")
