from django.http import JsonResponse
from django.shortcuts import render

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
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Our engineering team has been notified.",
            "support_email": "support@auditmate.com"
        }, status=500)

    return render(request, '500.html', status=500)
