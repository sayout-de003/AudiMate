import os
import sys
import django
import json
import requests

# Setup Django
sys.path.append('/Users/sayantande/audit_full_app/audit_ease')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from rest_framework_simplejwt.tokens import RefreshToken
from apps.users.models import User

# Get a user
user = User.objects.first()
if not user:
    print("No user found")
    sys.exit(1)

# Generate Token
refresh = RefreshToken.for_user(user)
access_token = str(refresh.access_token)

print(f"User: {user.email}")
print(f"Token: {access_token[:10]}...")

# Make Request
headers = {'Authorization': f'Bearer {access_token}'}
try:
    # 0. Get User Me
    url_me = 'http://127.0.0.1:8000/api/v1/users/me/'
    print(f"\nRequesting {url_me}...")
    resp_me = requests.get(url_me, headers=headers)
    print("User Me Response:")
    print(json.dumps(resp_me.json(), indent=2))

    # 1. Get User Orgs
    
    url = 'http://127.0.0.1:8000/api/v1/organizations/'
    print(f"\nRequesting {url}...")
    resp = requests.get(url, headers=headers)
    
    if resp.status_code == 200:
        data = resp.json()
        print("List Response (first item):")
        if data['results']:
            print(json.dumps(data['results'][0], indent=2))
            org_id = data['results'][0]['id']
            
            # 2. Get Org Detail
            url_detail = f'http://127.0.0.1:8000/api/v1/organizations/{org_id}/'
            print(f"\nRequesting Detail {url_detail}...")
            resp_detail = requests.get(url_detail, headers=headers)
            print("Detail Response:")
            print(json.dumps(resp_detail.json(), indent=2))
            
            detail_data = resp_detail.json()
            if 'subscription_status' in detail_data:
                print(f"\n✅ subscription_status FOUND: {detail_data['subscription_status']}")
            else:
                print("\n❌ subscription_status MISSING in Detail View")
                
        else:
            print("No organizations found for user.")
    else:
        print(f"Error {resp.status_code}: {resp.text}")

except Exception as e:
    print(f"Request failed: {e}")
