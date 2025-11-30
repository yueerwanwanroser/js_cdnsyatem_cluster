"""
防御引擎 API 服务 - 为 APISIX 提供防御分析接口
多用户隔离、支持租户配置
"""

import os
import logging
from typing import Dict, Optional
from flask import Flask, request, jsonify, g
from functools import wraps
import redis
import json
import time
from datetime import datetime
from threading import Thread

from defense_engine import (
    DefenseEngine, RequestProfile, ThreatLevel, 
    AttackType, ClusterCoordinator
)

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis 连接
redis_pool = redis.ConnectionPool(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True
)
redis_client = redis.Redis(connection_pool=redis_pool)

# 防御引擎实例缓存
engines = {}
engines_lock = {}

# 集群协调器
node_id = os.getenv('NODE_ID', 'node-1')
coordinator = ClusterCoordinator(redis_client, node_id)


def get_defense_engine(tenant_id: str) -> DefenseEngine:
    """获取或创建防御引擎实例（每个租户一个）"""
    if tenant_id not in engines:
        engines[tenant_id] = DefenseEngine(redis_client, node_id)
    return engines[tenant_id]


def require_tenant(f):
    """验证租户"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        tenant_id = request.headers.get('X-Tenant-ID') or request.args.get('tenant_id')
        
        if not tenant_id:
            return jsonify({'error': '缺少租户ID'}), 400
        
        # 验证租户是否存在
        if not redis_client.exists(f"tenant:{tenant_id}"):
            # 对于演示，自动创建租户
            redis_client.hset(f"tenant:{tenant_id}", mapping={
                'name': f'Tenant {tenant_id}',
                'created_at': str(datetime.now()),
                'status': 'active'
            })
        
        g.tenant_id = tenant_id
        return f(*args, **kwargs)
    
    return decorated_function


@app.before_request
def before_request():
    """请求前置处理"""
    g.request_start_time = time.time()


@app.after_request
def after_request(response):
    """请求后置处理"""
    elapsed = time.time() - g.request_start_time
    response.headers['X-Process-Time'] = str(elapsed)
    return response


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    try:
        redis_client.ping()
        return jsonify({
            'status': 'healthy',
            'node_id': node_id,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500


@app.route('/analyze', methods=['POST'])
@require_tenant
def analyze_request():
    """
    分析请求并返回防御决策
    
    POST /analyze
    {
        "request": {
            "request_id": "xxx",
            "timestamp": 1234567890,
            "client_ip": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            "path": "/api/data",
            "method": "GET",
            "headers": {},
            "payload_size": 1024,
            "user_id": "user-123"
        }
    }
    """
    try:
        data = request.get_json()
        tenant_id = g.tenant_id
        
        req_data = data.get('request', {})
        
        # 构建请求配置文件
        profile = RequestProfile(
            request_id=req_data.get('request_id', 'unknown'),
            timestamp=req_data.get('timestamp', time.time()),
            client_ip=req_data.get('client_ip', request.remote_addr),
            user_agent=req_data.get('user_agent', ''),
            path=req_data.get('path', '/'),
            method=req_data.get('method', 'GET'),
            headers=req_data.get('headers', {}),
            payload_size=req_data.get('payload_size', 0),
            user_id=req_data.get('user_id', 'anonymous'),
            tenant_id=tenant_id
        )
        
        # 处理请求
        engine = get_defense_engine(tenant_id)
        decision = engine.process_request(profile)
        
        # 记录到日志
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'request_id': profile.request_id,
            'tenant_id': tenant_id,
            'client_ip': profile.client_ip,
            'user_id': profile.user_id,
            'threat_score': profile.threat_score,
            'decision': decision.action,
            'reason': decision.reason
        }
        redis_client.lpush(f"logs:{tenant_id}", json.dumps(log_entry))
        redis_client.ltrim(f"logs:{tenant_id}", 0, 9999)
        
        # 发布事件
        coordinator.publish_event('request_analyzed', {
            'request_id': profile.request_id,
            'tenant_id': tenant_id,
            'threat_score': profile.threat_score,
            'decision': decision.action
        })
        
        return jsonify({
            'request_id': profile.request_id,
            'allow': decision.allow,
            'action': decision.action,
            'threat_level': decision.threat_level.name,
            'threat_score': decision.threat_score,
            'reason': decision.reason,
            'require_js_challenge': decision.require_js_challenge,
            'block_duration': decision.block_duration
        })
    
    except Exception as e:
        logger.error(f"分析请求失败: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/config', methods=['GET', 'POST'])
@require_tenant
def manage_config():
    """管理防御配置"""
    tenant_id = g.tenant_id
    
    if request.method == 'GET':
        # 获取配置
        engine = get_defense_engine(tenant_id)
        return jsonify({
            'config': engine.config,
            'tenant_id': tenant_id
        })
    
    elif request.method == 'POST':
        # 更新配置
        data = request.get_json()
        engine = get_defense_engine(tenant_id)
        engine.update_config(data.get('config', {}))
        
        # 同步到集群
        coordinator.sync_config(data.get('config', {}))
        
        return jsonify({'message': '配置已更新'})


@app.route('/blacklist', methods=['GET', 'POST', 'DELETE'])
@require_tenant
def manage_blacklist():
    """管理黑名单"""
    tenant_id = g.tenant_id
    
    if request.method == 'GET':
        # 获取黑名单
        pattern = f"blacklist:{tenant_id}:*"
        keys = redis_client.keys(pattern)
        blacklist = [key.replace(f"blacklist:{tenant_id}:", "") for key in keys]
        return jsonify({'blacklist': blacklist})
    
    elif request.method == 'POST':
        # 添加到黑名单
        data = request.get_json()
        ip = data.get('ip')
        duration = data.get('duration', 3600)
        
        if not ip:
            return jsonify({'error': 'IP 不能为空'}), 400
        
        engine = get_defense_engine(tenant_id)
        engine.add_to_blacklist(ip, tenant_id, duration)
        
        # 同步到集群
        coordinator.sync_blacklist(ip, tenant_id)
        
        return jsonify({'message': f'IP {ip} 已加入黑名单'})
    
    elif request.method == 'DELETE':
        # 从黑名单移除
        data = request.get_json()
        ip = data.get('ip')
        
        if not ip:
            return jsonify({'error': 'IP 不能为空'}), 400
        
        key = f"blacklist:{tenant_id}:{ip}"
        redis_client.delete(key)
        
        return jsonify({'message': f'IP {ip} 已从黑名单移除'})


@app.route('/whitelist', methods=['GET', 'POST', 'DELETE'])
@require_tenant
def manage_whitelist():
    """管理白名单"""
    tenant_id = g.tenant_id
    
    if request.method == 'GET':
        # 获取白名单
        pattern = f"whitelist:{tenant_id}:*"
        keys = redis_client.keys(pattern)
        whitelist = [key.replace(f"whitelist:{tenant_id}:", "") for key in keys]
        return jsonify({'whitelist': whitelist})
    
    elif request.method == 'POST':
        # 添加到白名单
        data = request.get_json()
        ip = data.get('ip')
        
        if not ip:
            return jsonify({'error': 'IP 不能为空'}), 400
        
        engine = get_defense_engine(tenant_id)
        engine.add_to_whitelist(ip, tenant_id)
        
        return jsonify({'message': f'IP {ip} 已加入白名单'})
    
    elif request.method == 'DELETE':
        # 从白名单移除
        data = request.get_json()
        ip = data.get('ip')
        
        if not ip:
            return jsonify({'error': 'IP 不能为空'}), 400
        
        key = f"whitelist:{tenant_id}:{ip}"
        redis_client.delete(key)
        
        return jsonify({'message': f'IP {ip} 已从白名单移除'})


@app.route('/statistics', methods=['GET'])
@require_tenant
def get_statistics():
    """获取统计信息"""
    tenant_id = g.tenant_id
    
    try:
        # 获取日志
        logs = redis_client.lrange(f"logs:{tenant_id}", 0, -1)
        
        stats = {
            'total_requests': len(logs),
            'blocked': 0,
            'rate_limited': 0,
            'challenged': 0,
            'allowed': 0,
            'avg_threat_score': 0.0,
            'top_ips': {},
            'top_threats': {}
        }
        
        threat_scores = []
        
        for log_str in logs:
            log = json.loads(log_str)
            threat_scores.append(log.get('threat_score', 0))
            
            ip = log.get('client_ip', 'unknown')
            stats['top_ips'][ip] = stats['top_ips'].get(ip, 0) + 1
            
            decision = log.get('decision')
            if decision == 'block':
                stats['blocked'] += 1
            elif decision == 'rate_limit':
                stats['rate_limited'] += 1
            elif decision == 'challenge':
                stats['challenged'] += 1
            else:
                stats['allowed'] += 1
        
        if threat_scores:
            stats['avg_threat_score'] = sum(threat_scores) / len(threat_scores)
        
        # 获取顶级 IP
        stats['top_ips'] = dict(sorted(
            stats['top_ips'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10])
        
        return jsonify(stats)
    
    except Exception as e:
        logger.error(f"获取统计失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/logs', methods=['GET'])
@require_tenant
def get_logs():
    """获取防御日志"""
    tenant_id = g.tenant_id
    limit = request.args.get('limit', 100, type=int)
    
    try:
        logs_raw = redis_client.lrange(f"logs:{tenant_id}", 0, limit - 1)
        logs = [json.loads(log) for log in logs_raw]
        return jsonify({'logs': logs})
    except Exception as e:
        logger.error(f"获取日志失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/sync/status', methods=['GET'])
def sync_status():
    """集群同步状态"""
    try:
        return jsonify({
            'node_id': node_id,
            'status': 'active',
            'timestamp': datetime.now().isoformat(),
            'redis_connected': redis_client.ping()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': '端点不存在'}), 404


@app.errorhandler(500)
def server_error(error):
    logger.error(f"服务器错误: {error}")
    return jsonify({'error': '内部服务器错误'}), 500


if __name__ == '__main__':
    logger.info(f"防御引擎 API 启动，节点 ID: {node_id}")
    
    # 启动 Flask 应用
    port = int(os.getenv('API_PORT', 5000))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True
    )
