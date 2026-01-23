from django.apps import AppConfig


class AuditsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audits'
    label = 'audits'

    def ready(self):
        from . import audit_registry
        audit_registry.register_models()
        import apps.audits.signals  # Register signals

