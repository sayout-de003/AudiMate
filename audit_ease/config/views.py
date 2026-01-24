from django.http import JsonResponse
from django.shortcuts import render
from django.db import connection
from django_redis import get_redis_connection
import logging

logger = logging.getLogger(__name__)

def health_check(request):
    """
    Health check endpoint for Load Balancers and Docker.
    Checks Database and Redis connectivity.
    """
    health_status = {
        "status": "healthy",
        "db": "unknown",
        "redis": "unknown"
    }
    status_code = 200

    # DB Check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status["db"] = "up"
    except Exception as e:
        health_status["db"] = "down"
        health_status["status"] = "unhealthy"
        status_code = 500
        logger.error("Health check failed: Database down", exc_info=True)

    # Redis Check
    try:
        conn = get_redis_connection("default")
        conn.ping()
        health_status["redis"] = "up"
    except Exception as e:
        health_status["redis"] = "down"
        health_status["status"] = "unhealthy"
        status_code = 500
        logger.error("Health check failed: Redis down", exc_info=True)

    return JsonResponse(health_status, status=status_code)

def custom_500(request):
    """
    Custom 500 error handler that returns JSON for API requests
    and a HTML page for browser requests.
    """
    # Check if request expects JSON
    is_api_request = (
        request.path.startswith('/api/') or 
        request.headers.get('Accept') == 'application/json'
    )

    if is_api_request:
        return JsonResponse({
            "status": "error",
            "code": "internal_server_error",
            "message": "An unexpected error occurred. Our engineering team has been notified.",
            "detail": "Please contact support@auditmate.com for assistance."
        }, status=500)

    return render(request, '500.html', status=500)

