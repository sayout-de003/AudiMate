import os
import django
import json

# Setup Django standalone
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django.conf import settings
from rest_framework.test import APIRequestFactory
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from utils.exceptions import custom_exception_handler
from config.views import custom_500
from django.http import HttpRequest

def test_validation_error():
    print("Testing ValidationError...")
    exc = ValidationError({"field": ["This field is required."]})
    context = {}
    response = custom_exception_handler(exc, context)
    print(json.dumps(response.data, indent=2))
    assert response.data['status'] == 'error'
    assert response.data['code'] == 'validation_error'
    assert 'field' in response.data['detail']

def test_not_found():
    print("\nTesting NotFound...")
    exc = NotFound()
    context = {}
    response = custom_exception_handler(exc, context)
    print(json.dumps(response.data, indent=2))
    assert response.data['status'] == 'error'
    assert response.data['code'] == 'not_found'

def test_custom_500():
    print("\nTesting Custom 500...")
    request = HttpRequest()
    request.path = '/api/test'
    response = custom_500(request)
    data = json.loads(response.content)
    print(json.dumps(data, indent=2))
    assert data['status'] == 'error'
    assert data['code'] == 'internal_server_error'

if __name__ == "__main__":
    test_validation_error()
    test_not_found()
    test_custom_500()
