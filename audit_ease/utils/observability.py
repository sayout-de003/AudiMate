import sentry_sdk
import logging

# Get a logger instance
logger = logging.getLogger(__name__)

def capture_exception(exception, context=None):
    """
    Manually capture an exception to Sentry and log it using structured logging.
    
    Usage:
        try:
            ...
        except Exception as e:
            capture_exception(e, context={"user_id": 123, "action": "audit"})
    
    Args:
        exception (Exception): The exception object to capture.
        context (dict, optional): Dictionary of extra context to send to Sentry and logs.
    """
    if context:
        # Add context to Sentry scope
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(exception)
    else:
        sentry_sdk.capture_exception(exception)
    
    # Log to local logs with structured data
    # python-json-logger will merge 'extra' fields into the JSON output
    log_extra = context if context else {}
    logger.error(str(exception), exc_info=True, extra=log_extra)

def capture_message(message, level="info", context=None):
    """
    Manually capture a message to Sentry and log it.
    
    Args:
        message (str): The message string.
        level (str): 'info', 'warning', 'error', 'debug', 'fatal'.
        context (dict, optional): Extra context data.
    """
    if context:
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_message(message, level=level)
    else:
        sentry_sdk.capture_message(message, level=level)
        
    log_extra = context if context else {}
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(message, extra=log_extra)
