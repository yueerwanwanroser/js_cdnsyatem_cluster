"""
Django models for CDN Defense System
"""
from django.db import models
from django.utils.translation import gettext_lazy as _


class Tenant(models.Model):
    """租户模型"""
    tenant_id = models.CharField(
        max_length=255,
        unique=True,
        help_text='Unique tenant identifier'
    )
    name = models.CharField(
        max_length=255,
        help_text='Tenant display name'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('Tenant')
        verbose_name_plural = _('Tenants')

    def __str__(self):
        return self.tenant_id


class TenantConfig(models.Model):
    """租户配置模型"""
    tenant = models.OneToOneField(
        Tenant,
        on_delete=models.CASCADE,
        related_name='config'
    )
    rate_limit = models.IntegerField(default=1000)
    threat_threshold = models.IntegerField(default=70)
    enabled_defense = models.BooleanField(default=True)
    js_challenge = models.BooleanField(default=True)
    bot_detection = models.BooleanField(default=False)
    config_data = models.JSONField(default=dict)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Tenant Config')
        verbose_name_plural = _('Tenant Configs')

    def __str__(self):
        return f'{self.tenant.tenant_id} Config v{self.version}'


class Route(models.Model):
    """路由模型"""
    route_id = models.CharField(max_length=255, unique=True)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='routes'
    )
    path = models.CharField(max_length=255)
    upstream = models.URLField()
    methods = models.JSONField(default=list)
    strip_path = models.BooleanField(default=True)
    enabled = models.BooleanField(default=True)
    plugins = models.JSONField(default=list)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Route')
        verbose_name_plural = _('Routes')
        unique_together = ('tenant', 'route_id')

    def __str__(self):
        return f'{self.route_id}'


class SSLCertificate(models.Model):
    """SSL 证书模型"""
    cert_id = models.CharField(max_length=255, unique=True)
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='ssl_certs'
    )
    domain = models.CharField(max_length=255)
    cert = models.TextField()  # PEM format
    key = models.TextField()   # PEM format
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('SSL Certificate')
        verbose_name_plural = _('SSL Certificates')

    def __str__(self):
        return f'{self.domain}'


class DefensePolicy(models.Model):
    """防御策略模型"""
    route = models.OneToOneField(
        Route,
        on_delete=models.CASCADE,
        related_name='defense_policy'
    )
    enabled = models.BooleanField(default=True)
    threat_threshold = models.IntegerField(default=75)
    challenge_type = models.CharField(
        max_length=50,
        choices=[
            ('js', 'JavaScript Challenge'),
            ('captcha', 'CAPTCHA Challenge'),
            ('fingerprint', 'Browser Fingerprint'),
        ],
        default='js'
    )
    js_fingerprint = models.BooleanField(default=True)
    rate_limit = models.IntegerField(default=1000)
    block_suspicious = models.BooleanField(default=True)
    config_data = models.JSONField(default=dict)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Defense Policy')
        verbose_name_plural = _('Defense Policies')

    def __str__(self):
        return f'{self.route.route_id} Policy'


class SyncLog(models.Model):
    """同步日志模型"""
    SYNC_TYPE_CHOICES = [
        ('config', 'Configuration Sync'),
        ('route', 'Route Sync'),
        ('ssl', 'SSL Sync'),
        ('defense', 'Defense Policy Sync'),
    ]

    node_id = models.CharField(max_length=255)
    sync_type = models.CharField(max_length=50, choices=SYNC_TYPE_CHOICES)
    resource_id = models.CharField(max_length=255)
    status = models.CharField(
        max_length=50,
        choices=[('success', 'Success'), ('failed', 'Failed'), ('pending', 'Pending')]
    )
    version = models.IntegerField()
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Sync Log')
        verbose_name_plural = _('Sync Logs')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.node_id} - {self.sync_type} - {self.status}'
