import requests
from django.conf import settings
from urllib.parse import urlencode

class GitHubOAuth:
    AUTH_URL = "https://github.com/login/oauth/authorize"
    TOKEN_URL = "https://github.com/login/oauth/access_token"
    API_URL = "https://api.github.com"

    def __init__(self):
        self.client_id = getattr(settings, 'GITHUB_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'GITHUB_CLIENT_SECRET', '')
        # Scopes: 'repo' gives access to private repos, 'read:org' for org membership
        self.scope = "repo read:org"
        
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "GitHub OAuth credentials are not configured. "
                "Please set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in your environment variables."
            ) 

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

    def exchange_code_for_token(self, code, redirect_uri=None):
        """Swaps the temporary code for a permanent access token."""
        headers = {"Accept": "application/json"}
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
        }
        # GitHub requires redirect_uri to match exactly what was used in authorization
        if redirect_uri:
            payload["redirect_uri"] = redirect_uri
        
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