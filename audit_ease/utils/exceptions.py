from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError

def custom_exception_handler(exc, context):
    """
    Custom exception handler that standardizes API error responses.
    """
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # If response is None, it means it's an unhandled exception (like 500)
    # which will be handled by the custom 500 view or Django's default handler.
    if response is not None:
        
        # Default structure
        custom_response_data = {
            "status": "error",
            "code": exc.__class__.__name__, # Default code from exception class name
            "message": "An error occurred.", # Default message
            "detail": response.data
        }

        # Handle Validation Errors specifically
        if isinstance(exc, ValidationError):
            custom_response_data["code"] = "validation_error"
            custom_response_data["message"] = "Invalid input data."
            # DRF already formats ValidationError detail as a list or dict, so we keep it.
        
        # Map specific codes to more readable messages if needed
        # (You can expand this mapping as needed)
        error_code_map = {
            "AuthenticationFailed": "Authentication failed.",
            "NotAuthenticated": "Authentication credentials were not provided.",
            "PermissionDenied": "You do not have permission to perform this action.",
            "NotFound": "The requested resource was not found.",
            "MethodNotAllowed": "Method not allowed for this resource.",
            "Throttled": "Request was throttled."
        }
        
        exception_name = exc.__class__.__name__
        if exception_name in error_code_map:
            custom_response_data["message"] = error_code_map[exception_name]
            
        # Refine the code to be snake_case if it isn't already handled
        # Simple conversion for standard exceptions
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', exception_name)
        snake_case_code = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
        if custom_response_data["code"] == exception_name:
             custom_response_data["code"] = snake_case_code

        # If 'detail' key exists in original response (DRF default), use it as detail
        # But for ValidationError, response.data IS the detail.
        # For others like NotFound, response.data is {'detail': 'Not found.'}
        if "detail" in response.data and not isinstance(exc, ValidationError):
             custom_response_data["detail"] = response.data["detail"]
        else:
             custom_response_data["detail"] = response.data

        response.data = custom_response_data

    return response
