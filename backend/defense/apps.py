"""
Apps configuration for CDN Defense System
"""
from django.apps import AppConfig


class DefenseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'defense'
    verbose_name = 'CDN Defense System'

    def ready(self):
        """初始化应用"""
        import defense.signals  # noqa
