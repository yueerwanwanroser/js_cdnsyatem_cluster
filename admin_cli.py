"""
CDN 防御系统管理工具
"""

import argparse
import requests
import json
from typing import Optional
import redis


class DefenseAdmin:
    """防御系统管理员"""
    
    def __init__(self, api_url: str = "http://localhost:5000", 
                 redis_host: str = "localhost"):
        self.api_url = api_url
        self.redis_client = redis.Redis(host=redis_host, decode_responses=True)
    
    def list_tenants(self):
        """列出所有租户"""
        pattern = "tenant:*"
        keys = self.redis_client.keys(pattern)
        
        print(f"\n{'租户ID':<20} {'状态':<10} {'创建时间':<20}")
        print("-" * 50)
        
        for key in keys:
            tenant_id = key.replace("tenant:", "")
            tenant_data = self.redis_client.hgetall(key)
            
            print(f"{tenant_id:<20} {tenant_data.get('status', 'unknown'):<10} {tenant_data.get('created_at', 'unknown'):<20}")
    
    def create_tenant(self, tenant_id: str):
        """创建租户"""
        tenant_data = {
            'name': f'Tenant {tenant_id}',
            'created_at': str(__import__('datetime').datetime.now()),
            'status': 'active'
        }
        
        self.redis_client.hset(f"tenant:{tenant_id}", mapping=tenant_data)
        print(f"✓ 租户 {tenant_id} 创建成功")
    
    def add_blacklist(self, tenant_id: str, ip: str, duration: int = 3600):
        """添加到黑名单"""
        headers = {"X-Tenant-ID": tenant_id}
        data = {"ip": ip, "duration": duration}
        
        response = requests.post(
            f"{self.api_url}/blacklist",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            print(f"✓ IP {ip} 已加入黑名单")
        else:
            print(f"✗ 添加失败: {response.text}")
    
    def add_whitelist(self, tenant_id: str, ip: str):
        """添加到白名单"""
        headers = {"X-Tenant-ID": tenant_id}
        data = {"ip": ip}
        
        response = requests.post(
            f"{self.api_url}/whitelist",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            print(f"✓ IP {ip} 已加入白名单")
        else:
            print(f"✗ 添加失败: {response.text}")
    
    def list_blacklist(self, tenant_id: str):
        """列出黑名单"""
        headers = {"X-Tenant-ID": tenant_id}
        
        response = requests.get(
            f"{self.api_url}/blacklist",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            blacklist = data.get('blacklist', [])
            
            print(f"\n租户 {tenant_id} 的黑名单 ({len(blacklist)} 个 IP):")
            print("-" * 50)
            
            for ip in blacklist:
                print(f"  - {ip}")
        else:
            print(f"✗ 获取失败: {response.text}")
    
    def list_whitelist(self, tenant_id: str):
        """列出白名单"""
        headers = {"X-Tenant-ID": tenant_id}
        
        response = requests.get(
            f"{self.api_url}/whitelist",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            whitelist = data.get('whitelist', [])
            
            print(f"\n租户 {tenant_id} 的白名单 ({len(whitelist)} 个 IP):")
            print("-" * 50)
            
            for ip in whitelist:
                print(f"  - {ip}")
        else:
            print(f"✗ 获取失败: {response.text}")
    
    def update_config(self, tenant_id: str, config: dict):
        """更新租户配置"""
        headers = {"X-Tenant-ID": tenant_id}
        data = {"config": config}
        
        response = requests.post(
            f"{self.api_url}/config",
            headers=headers,
            json=data
        )
        
        if response.status_code == 200:
            print(f"✓ 配置已更新")
        else:
            print(f"✗ 更新失败: {response.text}")
    
    def get_config(self, tenant_id: str):
        """获取租户配置"""
        headers = {"X-Tenant-ID": tenant_id}
        
        response = requests.get(
            f"{self.api_url}/config",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            config = data.get('config', {})
            
            print(f"\n租户 {tenant_id} 的配置:")
            print("-" * 50)
            
            for key, value in config.items():
                print(f"  {key}: {value}")
        else:
            print(f"✗ 获取失败: {response.text}")
    
    def get_statistics(self, tenant_id: str):
        """获取统计信息"""
        headers = {"X-Tenant-ID": tenant_id}
        
        response = requests.get(
            f"{self.api_url}/statistics",
            headers=headers
        )
        
        if response.status_code == 200:
            stats = response.json()
            
            print(f"\n租户 {tenant_id} 的统计信息:")
            print("-" * 50)
            print(f"总请求数: {stats.get('total_requests', 0)}")
            print(f"已阻止: {stats.get('blocked', 0)}")
            print(f"限流: {stats.get('rate_limited', 0)}")
            print(f"挑战: {stats.get('challenged', 0)}")
            print(f"已允许: {stats.get('allowed', 0)}")
            print(f"平均威胁分数: {stats.get('avg_threat_score', 0):.2f}")
            
            if stats.get('top_ips'):
                print(f"\n顶级 IP:")
                for ip, count in list(stats['top_ips'].items())[:5]:
                    print(f"  {ip}: {count} 次")
        else:
            print(f"✗ 获取失败: {response.text}")
    
    def get_logs(self, tenant_id: str, limit: int = 100):
        """获取防御日志"""
        headers = {"X-Tenant-ID": tenant_id}
        
        response = requests.get(
            f"{self.api_url}/logs?limit={limit}",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            logs = data.get('logs', [])
            
            print(f"\n租户 {tenant_id} 的最近防御日志 (最多 {limit} 条):")
            print("-" * 80)
            print(f"{'时间':<20} {'IP':<15} {'决策':<15} {'威胁分数':<10} {'原因':<20}")
            print("-" * 80)
            
            for log in logs[-20:]:  # 显示最后 20 条
                print(f"{log.get('timestamp', ''):<20} {log.get('client_ip', ''):<15} {log.get('decision', ''):<15} {log.get('threat_score', 0):<10} {log.get('reason', ''):<20}")
        else:
            print(f"✗ 获取失败: {response.text}")


def main():
    parser = argparse.ArgumentParser(description="CDN 防御系统管理工具")
    parser.add_argument("--api-url", default="http://localhost:5000", help="API 地址")
    parser.add_argument("--redis-host", default="localhost", help="Redis 主机")
    
    subparsers = parser.add_subparsers(dest="command")
    
    # 租户管理
    tenant_parser = subparsers.add_parser("tenant")
    tenant_parser.add_argument("action", choices=["list", "create"])
    tenant_parser.add_argument("--id", help="租户 ID")
    
    # 黑名单
    blacklist_parser = subparsers.add_parser("blacklist")
    blacklist_parser.add_argument("action", choices=["add", "remove", "list"])
    blacklist_parser.add_argument("--tenant-id", required=True, help="租户 ID")
    blacklist_parser.add_argument("--ip", help="IP 地址")
    blacklist_parser.add_argument("--duration", type=int, default=3600, help="黑名单持续时间（秒）")
    
    # 白名单
    whitelist_parser = subparsers.add_parser("whitelist")
    whitelist_parser.add_argument("action", choices=["add", "remove", "list"])
    whitelist_parser.add_argument("--tenant-id", required=True, help="租户 ID")
    whitelist_parser.add_argument("--ip", help="IP 地址")
    
    # 配置
    config_parser = subparsers.add_parser("config")
    config_parser.add_argument("action", choices=["get", "set"])
    config_parser.add_argument("--tenant-id", required=True, help="租户 ID")
    config_parser.add_argument("--key", help="配置键")
    config_parser.add_argument("--value", help="配置值")
    
    # 统计
    stats_parser = subparsers.add_parser("stats")
    stats_parser.add_argument("--tenant-id", required=True, help="租户 ID")
    
    # 日志
    logs_parser = subparsers.add_parser("logs")
    logs_parser.add_argument("--tenant-id", required=True, help="租户 ID")
    logs_parser.add_argument("--limit", type=int, default=100, help="日志数量限制")
    
    args = parser.parse_args()
    
    admin = DefenseAdmin(args.api_url, args.redis_host)
    
    if args.command == "tenant":
        if args.action == "list":
            admin.list_tenants()
        elif args.action == "create":
            if not args.id:
                print("✗ 需要指定租户 ID (--id)")
                return
            admin.create_tenant(args.id)
    
    elif args.command == "blacklist":
        if args.action == "add":
            if not args.ip:
                print("✗ 需要指定 IP (--ip)")
                return
            admin.add_blacklist(args.tenant_id, args.ip, args.duration)
        elif args.action == "list":
            admin.list_blacklist(args.tenant_id)
    
    elif args.command == "whitelist":
        if args.action == "add":
            if not args.ip:
                print("✗ 需要指定 IP (--ip)")
                return
            admin.add_whitelist(args.tenant_id, args.ip)
        elif args.action == "list":
            admin.list_whitelist(args.tenant_id)
    
    elif args.command == "config":
        if args.action == "get":
            admin.get_config(args.tenant_id)
        elif args.action == "set":
            if not args.key or args.value is None:
                print("✗ 需要指定键 (--key) 和值 (--value)")
                return
            config = {args.key: args.value}
            admin.update_config(args.tenant_id, config)
    
    elif args.command == "stats":
        admin.get_statistics(args.tenant_id)
    
    elif args.command == "logs":
        admin.get_logs(args.tenant_id, args.limit)


if __name__ == "__main__":
    main()
