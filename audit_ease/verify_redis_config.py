import os
import django
from django.conf import settings
from django.core.cache import cache

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
django.setup()

def verify_redis():
    print("--- Verifying Redis Configuration ---")
    
    # 1. Check CACHES setting
    backend = settings.CACHES['default']['BACKEND']
    location = settings.CACHES['default']['LOCATION']
    print(f"Cache Backend: {backend}")
    print(f"Cache Location: {location}")
    
    if "RedisCache" not in backend:
        print("FAIL: Cache backend is not RedisCache")
        return

    # 2. Test Cache Set/Get
    try:
        cache.set("test_key", "redis_works", timeout=30)
        value = cache.get("test_key")
        print(f"Cache Get Result: {value}")
        
        if value == "redis_works":
            print("SUCCESS: Redis cache is working!")
        else:
            print("FAIL: Redis cache returned incorrect value.")
            
    except Exception as e:
        print(f"FAIL: Error connecting to cache: {e}")

    # 3. Check Celery Settings
    print(f"Celery Broker: {settings.CELERY_BROKER_URL}")
    if "redis" in settings.CELERY_BROKER_URL:
        print("SUCCESS: Celery broker is using Redis.")
    else:
        print("FAIL: Celery broker is NOT using Redis.")

if __name__ == "__main__":
    verify_redis()
