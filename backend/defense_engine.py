"""
CDN 防御引擎 - 核心防御逻辑
支持多节点集群、多用户隔离、实时威胁检测
"""

import time
import hashlib
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from datetime import datetime, timedelta
import threading
import redis
from enum import Enum

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """威胁等级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class AttackType(Enum):
    """攻击类型"""
    NORMAL = 0
    SLOW_ATTACK = 1           # 慢速攻击
    CC_ATTACK = 2             # CC 攻击
    SQL_INJECTION = 3         # SQL 注入
    XSS_ATTACK = 4            # XSS 攻击
    BOT_ATTACK = 5            # 机器人攻击
    DDOS_VOLUMETRIC = 6       # 体积型 DDoS
    DDOS_PROTOCOL = 7         # 协议型 DDoS
    DDOS_APPLICATION = 8      # 应用层 DDoS
    PATTERN_ANOMALY = 9       # 模式异常


@dataclass
class RequestProfile:
    """请求配置文件"""
    request_id: str
    timestamp: float
    client_ip: str
    user_agent: str
    path: str
    method: str
    headers: Dict
    payload_size: int
    user_id: str
    tenant_id: str
    
    # 风险指标
    has_js_challenge: bool = False
    js_passed: bool = False
    fingerprint_matched: bool = False
    is_bot: bool = False
    threat_score: float = 0.0
    attack_type: AttackType = AttackType.NORMAL


@dataclass
class DefenseDecision:
    """防御决策"""
    allow: bool
    threat_level: ThreatLevel
    action: str  # allow, block, challenge, rate_limit
    reason: str
    threat_score: float
    require_js_challenge: bool = False
    block_duration: int = 0  # 秒


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def check_rate_limit(self, key: str, limit: int, window: int) -> Tuple[bool, int]:
        """
        检查速率限制
        :param key: 限制键（如 IP）
        :param limit: 时间窗口内允许的最大请求数
        :param window: 时间窗口（秒）
        :return: (是否超限, 当前计数)
        """
        pipeline = self.redis.pipeline()
        current_time = int(time.time())
        bucket_key = f"rate_limit:{key}:{current_time // window}"
        
        pipeline.incr(bucket_key)
        pipeline.expire(bucket_key, window)
        results = pipeline.execute()
        
        count = results[0]
        return count > limit, count


class AnomalyDetector:
    """异常检测器"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.window_size = 300  # 5分钟窗口
        
    def detect_anomalies(self, profile: RequestProfile) -> Tuple[bool, Dict]:
        """
        检测异常模式
        :return: (是否异常, 异常详情)
        """
        anomalies = {}
        is_anomaly = False
        
        # 1. 检测快速连续请求
        key = f"request_pattern:{profile.client_ip}:{profile.user_id}"
        timestamps = self.redis.lrange(key, -10, -1)
        
        if len(timestamps) >= 10:
            recent_timestamps = [float(ts) for ts in timestamps[-10:]]
            time_diffs = [recent_timestamps[i+1] - recent_timestamps[i] 
                         for i in range(len(recent_timestamps)-1)]
            avg_diff = sum(time_diffs) / len(time_diffs)
            
            if avg_diff < 0.1:  # 平均间隔小于 100ms
                anomalies['rapid_requests'] = {
                    'avg_interval': avg_diff,
                    'threshold': 0.1
                }
                is_anomaly = True
        
        # 2. 检测多路径扫描
        key = f"path_scan:{profile.client_ip}:{profile.user_id}"
        paths = self.redis.smembers(key)
        
        if len(paths) > 50:  # 5分钟内访问超过50个不同路径
            anomalies['path_scanning'] = {
                'unique_paths': len(paths),
                'threshold': 50
            }
            is_anomaly = True
        
        # 3. 检测用户代理异常
        key = f"useragent_pattern:{profile.client_ip}:{profile.user_id}"
        user_agents = self.redis.smembers(key)
        
        if len(user_agents) > 20:  # 同一IP多个用户代理
            anomalies['ua_spoofing'] = {
                'unique_agents': len(user_agents),
                'threshold': 20
            }
            is_anomaly = True
        
        # 记录当前请求
        self.redis.lpush(key, profile.timestamp)
        self.redis.expire(key, self.window_size)
        
        return is_anomaly, anomalies
    
    def calculate_threat_score(self, profile: RequestProfile, 
                              anomalies: Dict) -> float:
        """计算威胁分数 (0-100)"""
        score = 0.0
        
        # 基础分数
        if profile.is_bot:
            score += 30
        
        if anomalies.get('rapid_requests'):
            score += 20
        
        if anomalies.get('path_scanning'):
            score += 25
        
        if anomalies.get('ua_spoofing'):
            score += 15
        
        # JS 验证状态
        if not profile.js_passed and profile.has_js_challenge:
            score += 10
        
        # 指纹匹配
        if not profile.fingerprint_matched:
            score += 5
        
        # 负载大小异常
        if profile.payload_size > 1000000:  # 超过 1MB
            score += 10
        
        # 黑名单 IP
        if self._is_blacklisted(profile.client_ip, profile.tenant_id):
            score += 50
        
        return min(score, 100.0)
    
    def _is_blacklisted(self, ip: str, tenant_id: str) -> bool:
        """检查 IP 是否在黑名单"""
        key = f"blacklist:{tenant_id}:{ip}"
        return self.redis.exists(key) > 0


class DefenseEngine:
    """CDN 防御引擎"""
    
    def __init__(self, redis_client: redis.Redis, node_id: str):
        self.redis = redis_client
        self.node_id = node_id
        self.rate_limiter = RateLimiter(redis_client)
        self.anomaly_detector = AnomalyDetector(redis_client)
        
        # 配置
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载防御配置"""
        config = self.redis.hgetall("defense:config")
        return {k.decode(): v.decode() for k, v in config.items()} if config else self._default_config()
    
    def _default_config(self) -> Dict:
        """默认防御配置"""
        return {
            'rate_limit_per_minute': '100',
            'rate_limit_per_hour': '10000',
            'js_challenge_threshold': '30',
            'block_threshold': '70',
            'bot_detection_enabled': 'true',
            'anomaly_detection_enabled': 'true'
        }
    
    def process_request(self, profile: RequestProfile) -> DefenseDecision:
        """
        处理请求 - 主防御流程
        """
        logger.info(f"处理请求: {profile.request_id} from {profile.client_ip}")
        
        # 1. 检查白名单
        if self._is_whitelisted(profile):
            return DefenseDecision(
                allow=True,
                threat_level=ThreatLevel.LOW,
                action='allow',
                reason='在白名单中',
                threat_score=0.0
            )
        
        # 2. 速率限制检查
        is_limited, count = self.rate_limiter.check_rate_limit(
            f"{profile.tenant_id}:{profile.client_ip}",
            limit=int(self.config['rate_limit_per_minute']),
            window=60
        )
        
        if is_limited:
            logger.warning(f"超出速率限制: {profile.client_ip}, 计数: {count}")
            return DefenseDecision(
                allow=False,
                threat_level=ThreatLevel.HIGH,
                action='rate_limit',
                reason='超出速率限制',
                threat_score=75.0,
                block_duration=60
            )
        
        # 3. 异常检测
        is_anomaly, anomalies = self.anomaly_detector.detect_anomalies(profile)
        threat_score = self.anomaly_detector.calculate_threat_score(profile, anomalies)
        profile.threat_score = threat_score
        
        logger.info(f"威胁分数: {threat_score}, 异常: {anomalies}")
        
        # 4. 威胁等级评定
        if threat_score >= 70:
            threat_level = ThreatLevel.CRITICAL
        elif threat_score >= 50:
            threat_level = ThreatLevel.HIGH
        elif threat_score >= 30:
            threat_level = ThreatLevel.MEDIUM
        else:
            threat_level = ThreatLevel.LOW
        
        # 5. 决策生成
        if threat_score >= float(self.config.get('block_threshold', 70)):
            return DefenseDecision(
                allow=False,
                threat_level=threat_level,
                action='block',
                reason=f'威胁分数过高: {threat_score}',
                threat_score=threat_score,
                block_duration=3600
            )
        
        if threat_score >= float(self.config.get('js_challenge_threshold', 30)):
            return DefenseDecision(
                allow=True,
                threat_level=threat_level,
                action='challenge',
                reason='需要 JS 验证',
                threat_score=threat_score,
                require_js_challenge=True
            )
        
        # 6. 允许请求
        return DefenseDecision(
            allow=True,
            threat_level=threat_level,
            action='allow',
            reason='通过防御检查',
            threat_score=threat_score
        )
    
    def _is_whitelisted(self, profile: RequestProfile) -> bool:
        """检查是否在白名单"""
        key = f"whitelist:{profile.tenant_id}:{profile.client_ip}"
        return self.redis.exists(key) > 0
    
    def add_to_blacklist(self, ip: str, tenant_id: str, duration: int = 3600):
        """添加到黑名单"""
        key = f"blacklist:{tenant_id}:{ip}"
        self.redis.setex(key, duration, "1")
        logger.info(f"IP {ip} 加入黑名单 {duration}秒")
    
    def add_to_whitelist(self, ip: str, tenant_id: str, duration: int = 0):
        """添加到白名单"""
        key = f"whitelist:{tenant_id}:{ip}"
        if duration > 0:
            self.redis.setex(key, duration, "1")
        else:
            self.redis.set(key, "1")
        logger.info(f"IP {ip} 加入白名单")
    
    def update_config(self, config: Dict):
        """更新防御配置"""
        pipe = self.redis.pipeline()
        for key, value in config.items():
            pipe.hset("defense:config", key, str(value))
        pipe.execute()
        self.config = self._load_config()
        logger.info("防御配置已更新")


class ClusterCoordinator:
    """集群协调器 - 多节点同步"""
    
    def __init__(self, redis_client: redis.Redis, node_id: str):
        self.redis = redis_client
        self.node_id = node_id
        self.publish_channel = f"defense:events"
    
    def publish_event(self, event_type: str, data: Dict):
        """发布事件到集群"""
        event = {
            'type': event_type,
            'node_id': self.node_id,
            'timestamp': time.time(),
            'data': data
        }
        self.redis.publish(self.publish_channel, json.dumps(event))
        logger.info(f"发布事件: {event_type}")
    
    def sync_blacklist(self, ip: str, tenant_id: str):
        """同步黑名单到集群"""
        self.publish_event('blacklist_update', {
            'ip': ip,
            'tenant_id': tenant_id,
            'action': 'add'
        })
    
    def sync_config(self, config: Dict):
        """同步配置到集群"""
        self.publish_event('config_update', config)


if __name__ == '__main__':
    # 示例使用
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    engine = DefenseEngine(redis_client, 'node-1')
    
    # 创建测试请求
    profile = RequestProfile(
        request_id='test-001',
        timestamp=time.time(),
        client_ip='192.168.1.100',
        user_agent='Mozilla/5.0',
        path='/api/data',
        method='GET',
        headers={},
        payload_size=1024,
        user_id='user-123',
        tenant_id='tenant-001'
    )
    
    # 处理请求
    decision = engine.process_request(profile)
    print(f"决策: {decision}")
