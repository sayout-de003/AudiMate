from django.apps import AppConfig


from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.users'  # <--- The new Python path
    label = 'users'      # <--- KEEPS THE OLD DB RELATIONS ALIVE
