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
        # 'read:user' is needed to get the authenticated user's profile
        self.scope = "repo read:org read:user"
        
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
        import logging
        logger = logging.getLogger(__name__)
        
        headers = {"Accept": "application/json"}
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
        }
        # GitHub requires redirect_uri to match exactly what was used in authorization
        if redirect_uri:
            payload["redirect_uri"] = redirect_uri
        
        # GitHub OAuth expects form-encoded data, not JSON
        logger.info(f"Exchanging OAuth code for token with redirect_uri: {redirect_uri}")
        try:
            response = requests.post(self.TOKEN_URL, data=payload, headers=headers, timeout=10)
            
            # Log response status for debugging
            logger.info(f"Token exchange response status: {response.status_code}")
            
            # If request failed, log the full error response
            if not response.ok:
                error_body = response.text
                logger.error(f"Token exchange error response: {error_body}")
                try:
                    error_json = response.json()
                    logger.error(f"Token exchange error JSON: {error_json}")
                except:
                    pass
            
            response.raise_for_status()
            token_data = response.json()
            
            # Validate that we got an access token
            if 'access_token' not in token_data:
                logger.error(f"Token exchange response missing access_token: {token_data}")
                raise ValueError("GitHub token exchange did not return an access_token")
            
            # Validate the access token is not empty
            access_token_value = token_data.get('access_token', '')
            if not access_token_value or not isinstance(access_token_value, str) or len(access_token_value.strip()) == 0:
                logger.error(f"Token exchange returned empty or invalid access_token: type={type(access_token_value)}, length={len(access_token_value) if access_token_value else 0}")
                raise ValueError("GitHub token exchange returned an empty or invalid access_token")
            
            logger.info(f"Successfully received access token with scopes: {token_data.get('scope', 'N/A')}")
            logger.info(f"Access token length: {len(access_token_value)}")
            logger.info(f"Access token preview: {access_token_value[:10]}..." if len(access_token_value) >= 10 else "Token too short")
            return token_data # Returns {'access_token': '...', 'scope': '...', ...}
        except requests.exceptions.Timeout:
            logger.error("Token exchange request timed out")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Token exchange request failed: {type(e).__name__}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise

    def get_user_info(self, access_token):
        """Fetches the authenticated GitHub user's ID/Login."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Validate token before use
        if not access_token:
            raise ValueError("Access token is None or empty")
        
        # Ensure token is clean (strip whitespace)
        if isinstance(access_token, str):
            access_token = access_token.strip()
        else:
            access_token = str(access_token).strip()
        
        if not access_token:
            raise ValueError("Access token is empty after cleaning")
        
        # Log token info for debugging (without exposing the actual token)
        logger.info(f"Using access token (length: {len(access_token)}, starts with: {access_token[:4]}...)")
        
        headers = {
            # GitHub now requires 'Bearer' prefix for OAuth tokens
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        try:
            logger.info(f"Fetching GitHub user info from {self.API_URL}/user")
            response = requests.get(f"{self.API_URL}/user", headers=headers, timeout=10)
            
            # Log response details for debugging
            logger.info(f"GitHub API response status: {response.status_code}")
            
            # If request failed, log the full error response
            if not response.ok:
                error_body = response.text
                logger.error(f"GitHub API error response: {error_body}")
                try:
                    error_json = response.json()
                    logger.error(f"GitHub API error JSON: {error_json}")
                except:
                    pass
            
            response.raise_for_status()
            user_data = response.json()
            logger.info(f"Successfully fetched GitHub user: {user_data.get('login', 'unknown')}")
            return user_data
        except requests.exceptions.Timeout:
            logger.error("GitHub API request timed out")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API request failed: {type(e).__name__}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            raise