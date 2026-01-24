import os
import sys
import django
import logging

# Setup Django
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.base")
django.setup()

from utils.observability import capture_exception, capture_message

logger = logging.getLogger("test_logger")

print("\n--- Testing Structured Logging ---")
logger.info("This is a test message", extra={"user_id": 123, "action": "test"})

print("\n--- Testing capture_exception (Mocking Sentry) ---")
try:
    1 / 0
except Exception as e:
    capture_exception(e, context={"context_key": "context_value"})

print("\n--- Testing capture_message ---")
capture_message("Manual message capture", level="warning", context={"extra_info": "foo"})
