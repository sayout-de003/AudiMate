import requests
from django.conf import settings
from urllib.parse import urlencode

class GitHubOAuth:
    AUTH_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    API_URL = "https://api.github.com"

    def __init__(self):
        self.client_id = settings.GITHUB_CLIENT_ID
        self.client_secret = settings.GITHUB_CLIENT_SECRET
        # Scopes: 'repo' gives access to private repos, 'read:org' for org membership
        self.scope = "repo read:org" 

    def get_authorization_url(self, redirect_uri=None):
        """Generates the URL to send the user to GitHub."""
        params = {
            "client_id": self.client_id,
            "scope": self.scope,
            "response_type": "code",
        }
        if redirect_uri:
            params["redirect_uri"] = redirect_uri
            
        return f"{self.AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_token(self, code):
        """Swaps the temporary code for a permanent access token."""
        headers = {"Accept": "application/json"}
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
        }
        
        response = requests.post(self.TOKEN_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json() # Returns {'access_token': '...', 'scope': '...', ...}

    def get_user_info(self, access_token):
        """Fetches the authenticated GitHub user's ID/Login."""
        headers = {
            "Authorization": f"token {access_token}",
            "Accept": "application/json"
        }
        response = requests.get(f"{self.API_URL}/user", headers=headers)
        response.raise_for_status()
        return response.json()