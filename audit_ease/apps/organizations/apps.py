from django.apps import AppConfig


class OrganizationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.organizations'
    label = 'organizations'
    def ready(self):
        """Register signal handlers when app is ready."""
        import apps.organizations.signals  # noqa