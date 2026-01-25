from .base import * # noqa
from .base import env

# 1. General
DEBUG = True
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-v^!_&development-key-do-not-use-in-production"
)
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1", "testserver"]

# 2. CORS (Allow everything in Dev)
# 2. CORS
# When CORS_ALLOW_CREDENTIALS is True (in base.py), we cannot use ALLOW_ALL_ORIGINS = True.
# We must use specific origins.
CORS_ALLOW_ALL_ORIGINS = False




# 4. WhiteNoise (Optional for dev, but good to test)
# INSTALLED_APPS += ["whitenoise.runserver_nostatic"]

# 5. REST Framework (Browsable API is helpful in Dev)
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
)