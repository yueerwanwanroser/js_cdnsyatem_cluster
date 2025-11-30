"""
CDN 防御系统配置文件示例
"""

# 基础配置
BASE_CONFIG = {
    # 防御引擎配置
    'defense': {
        # 速率限制
        'rate_limit': {
            'per_minute': 100,      # 每分钟请求数
            'per_hour': 10000,      # 每小时请求数
            'per_day': 1000000,     # 每天请求数
        },
        
        # 威胁评分阈值
        'thresholds': {
            'js_challenge': 30,     # JS 挑战阈值
            'rate_limit': 50,       # 限流阈值
            'block': 70,            # 阻止阈值
        },
        
        # 功能开关
        'features': {
            'bot_detection': True,
            'anomaly_detection': True,
            'js_challenge': True,
            'fingerprint_validation': True,
        }
    },
    
    # APISIX 网关配置
    'apisix': {
        'admin_api': 'http://localhost:9180',
        'gateway_url': 'http://localhost:9080',
        'routes': [
            {
                'name': 'protected-api',
                'uri': '/api/*',
                'plugins': {
                    'cdn-defense': {
                        'defense_engine_url': 'http://defense-api:5000',
                        'redis_host': 'redis',
                        'redis_port': 6379,
                        'enable_js_challenge': True,
                    }
                }
            }
        ]
    },
    
    # Redis 配置
    'redis': {
        'host': 'localhost',
        'port': 6379,
        'db': 0,
        'password': None,
    },
    
    # 日志配置
    'logging': {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file': 'logs/defense.log',
    },
    
    # 监控配置
    'monitoring': {
        'prometheus_enabled': True,
        'prometheus_port': 9090,
        'grafana_enabled': True,
        'grafana_port': 3000,
        'metrics_interval': 15,  # 秒
    }
}

# 租户配置示例
TENANT_CONFIG = {
    'tenant-001': {
        'name': '示例租户',
        'rate_limit': {
            'per_minute': 100,
            'per_hour': 10000,
        },
        'thresholds': {
            'js_challenge': 30,
            'rate_limit': 50,
            'block': 70,
        },
        'whitelist': [
            '10.0.0.0/8',           # 内部 IP
            '192.168.0.0/16',       # 本地网络
        ],
        'blacklist': [],
        'js_defense_enabled': True,
        'anomaly_detection_enabled': True,
    }
}

# 防御策略配置
DEFENSE_POLICIES = {
    'strict': {
        'rate_limit_per_minute': 50,
        'js_challenge_threshold': 20,
        'block_threshold': 60,
        'bot_detection_enabled': True,
        'anomaly_detection_enabled': True,
    },
    'moderate': {
        'rate_limit_per_minute': 100,
        'js_challenge_threshold': 30,
        'block_threshold': 70,
        'bot_detection_enabled': True,
        'anomaly_detection_enabled': True,
    },
    'lenient': {
        'rate_limit_per_minute': 200,
        'js_challenge_threshold': 50,
        'block_threshold': 85,
        'bot_detection_enabled': False,
        'anomaly_detection_enabled': False,
    }
}

# 日志级别
LOG_LEVELS = {
    'DEBUG': 10,
    'INFO': 20,
    'WARNING': 30,
    'ERROR': 40,
    'CRITICAL': 50,
}

# 环境变量默认值
ENV_DEFAULTS = {
    'REDIS_HOST': 'localhost',
    'REDIS_PORT': '6379',
    'API_PORT': '5000',
    'NODE_ID': 'node-1',
    'DEBUG': 'false',
    'APISIX_HOST': 'localhost',
    'APISIX_PORT': '9080',
    'APISIX_ADMIN_PORT': '9180',
}

# 攻击特征库
ATTACK_SIGNATURES = {
    'sql_injection': [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bSELECT\b.*\bFROM\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bUPDATE\b.*\bSET\b)",
    ],
    'xss': [
        r"(<script\b)",
        r"(javascript:)",
        r"(onerror=)",
        r"(onclick=)",
        r"(onload=)",
    ],
    'path_traversal': [
        r"(\.\./)",
        r"(\.\.\\)",
        r"(%2e%2e/)",
        r"(%252e%252e/)",
    ]
}

# 机器人特征
BOT_SIGNATURES = {
    'user_agents': [
        'bot',
        'crawler',
        'spider',
        'scraper',
        'curl',
        'wget',
        'python',
        'java',
        'headless',
        'phantom',
        'puppeteer',
    ]
}

# 异常检测参数
ANOMALY_DETECTION_CONFIG = {
    'rapid_request_threshold': 0.1,      # 100ms
    'path_scan_threshold': 50,           # 50 个不同路径
    'ua_spoofing_threshold': 20,         # 20 个不同 UA
    'sliding_window': 300,               # 5 分钟窗口
}

# 性能优化参数
PERFORMANCE_CONFIG = {
    'cache_ttl': 300,                   # 缓存 5 分钟
    'connection_pool_size': 100,        # Redis 连接池大小
    'request_timeout': 5,               # 请求超时 5 秒
    'worker_threads': 10,               # 工作线程数
}

if __name__ == '__main__':
    import json
    
    print("CDN 防御系统配置")
    print("=" * 50)
    print(json.dumps(BASE_CONFIG, indent=2, ensure_ascii=False))
