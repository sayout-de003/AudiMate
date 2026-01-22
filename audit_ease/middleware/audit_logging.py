import time
import json
import logging
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

# Get a specific logger for audits so you can route these logs 
# to a separate file or service (e.g., /var/log/audit.log)
logger = logging.getLogger("audit")

class AuditLogMiddleware:
    """
    Middleware to capture detailed request/response lifecycles.
    
    Features:
    1. Structured JSON Logging (Machine readable)
    2. Sensitive Data Redaction (GDPR/Compliance)
    3. Performance Tracking (Duration in ms)
    4. Context Awareness (User, Org, IP)
    """

    def __init__(self, get_response):
        self.get_response = get_response
        
        # Paths to ignore (Health checks, static files, admin assets) 
        # to prevent log flooding.
        self.skip_paths = [
            '/health/', 
            '/static/', 
            '/favicon.ico', 
            '/admin/jsi18n/'
        ]
        
        # Keys to automatically redact from request bodies
        self.sensitive_keys = {
            'password', 'token', 'access_token', 'refresh_token', 
            'authorization', 'secret', 'credit_card', 'cvv'
        }

    def __call__(self, request):
        # 1. Start Timer
        start_time = time.time()

        # 2. Process Request
        response = self.get_response(request)

        # 3. Calculate Duration
        duration_ms = (time.time() - start_time) * 1000

        # 4. Check Skip Logic
        if any(request.path.startswith(path) for path in self.skip_paths):
            return response

        # 5. Build Log Payload
        try:
            log_payload = self._build_log_entry(request, response, duration_ms)
            # Log as JSON string for easy parsing by external tools
            logger.info(json.dumps(log_payload))
        except Exception as e:
            # Fallback to prevent middleware from crashing the app
            logger.error(f"Failed to write audit log: {str(e)}")

        return response

    def _build_log_entry(self, request, response, duration_ms):
        """Constructs the structured log dictionary."""
        
        user = request.user
        
        # Extract IP (Handle proxy headers like Nginx/AWS ELB)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')

        # Safely get Organization from previous middleware (if exists)
        org_context = getattr(request, 'organization', None)
        org_id = str(org_context.id) if org_context else None

        entry = {
            "timestamp": time.time(),
            "env": getattr(settings, 'DJANGO_ENV', 'production'),
            "level": "AUDIT",
            "request": {
                "method": request.method,
                "path": request.path,
                "ip": ip_address,
                "user_agent": request.META.get('HTTP_USER_AGENT', ''),
                "user_id": str(user.id) if user.is_authenticated else "Anonymous",
                "user_email": user.email if user.is_authenticated else None,
                "org_id": org_id,
            },
            "response": {
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            }
        }

        # Optional: Log Request Body for state-changing methods
        # Note: Be cautious with large bodies or file uploads
        if request.method in ['POST', 'PUT', 'PATCH']:
            entry["request"]["body"] = self._get_cleaned_body(request)

        return entry

    def _get_cleaned_body(self, request):
        """
        Safely parses and cleans the request body.
        Only attempts to parse JSON content.
        """
        if request.content_type != 'application/json':
            return "Non-JSON Body"

        try:
            # Django 3.2+ request.body can be accessed even after read 
            # if DATA_UPLOAD_MAX_MEMORY_SIZE isn't exceeded.
            if not request.body:
                return {}
            
            data = json.loads(request.body)
            return self._redact_recursive(data)
        except Exception:
            return "Unreadable/Binary Body"

    def _redact_recursive(self, data):
        """Recursively scrubs sensitive keys from a dictionary."""
        if isinstance(data, dict):
            return {
                k: ("***REDACTED***" if k.lower() in self.sensitive_keys else self._redact_recursive(v))
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self._redact_recursive(item) for item in data]
        return data