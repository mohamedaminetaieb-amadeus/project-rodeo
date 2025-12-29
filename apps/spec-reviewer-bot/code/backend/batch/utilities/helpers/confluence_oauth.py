"""
OAuth2 authentication handler for Confluence Cloud.
Implements the OAuth2 authorization code flow.
"""
import requests
import logging
import traceback
import secrets
import json
from typing import Optional, Dict, Tuple
from urllib.parse import urlencode, quote
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ConfluenceOAuth2:
    """
    Handles OAuth2 authentication flow for Confluence Cloud.
    Implements the authorization code flow.
    
    Reference: https://developer.atlassian.com/cloud/confluence/oauth-2-authorization-code-grants-3lo-3lo/
    """

    # Confluence OAuth2 endpoints
    AUTHORIZATION_URL = "https://auth.atlassian.com/authorize"
    TOKEN_URL = "https://auth.atlassian.com/oauth/token"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ):
        """
        Initialize OAuth2 handler.

        Args:
            client_id: OAuth2 Client ID from Atlassian
            client_secret: OAuth2 Client Secret from Atlassian
            redirect_uri: Redirect URI registered in Atlassian (e.g., http://localhost:8501/auth/callback)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, scopes: Optional[list] = None) -> Tuple[str, str]:
        """
        Generate authorization URL for user to visit.

        Args:
            scopes: List of requested scopes. Defaults to common scopes.

        Returns:
            Tuple of (authorization_url, state) - state should be stored to verify callback
        """
        if scopes is None:
            scopes = [
                "read:confluence-content.all",
                "search:confluence",
                "offline_access",
            ]

        # Generate PKCE challenge (for security)
        state = secrets.token_urlsafe(32)

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "state": state,
            "prompt": "consent",  # Force consent screen for clear permissions
        }

        auth_url = f"{self.AUTHORIZATION_URL}?{urlencode(params)}"
        return auth_url, state

    def exchange_code_for_token(self, auth_code: str) -> Dict:
        """
        Exchange authorization code for access token.

        Args:
            auth_code: Authorization code from callback

        Returns:
            Token response dictionary with keys: access_token, refresh_token, expires_in, etc.
        """
        try:
            data = {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": auth_code,
                "redirect_uri": self.redirect_uri,
            }

            response = requests.post(self.TOKEN_URL, data=data)
            response.raise_for_status()

            token_data = response.json()
            # Add timestamp for expiration tracking
            token_data["obtained_at"] = datetime.utcnow().isoformat()

            logger.info("Successfully obtained OAuth2 access token")
            return token_data

        except Exception as e:
            logger.error(f"Error exchanging auth code for token: {traceback.format_exc()}")
            raise ValueError(f"Failed to exchange authorization code: {str(e)}")

    def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        Refresh an access token using a refresh token.

        Args:
            refresh_token: Refresh token from previous authorization

        Returns:
            New token response dictionary
        """
        try:
            data = {
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
            }

            response = requests.post(self.TOKEN_URL, data=data)
            response.raise_for_status()

            token_data = response.json()
            token_data["obtained_at"] = datetime.utcnow().isoformat()

            logger.info("Successfully refreshed OAuth2 access token")
            return token_data

        except Exception as e:
            logger.error(f"Error refreshing access token: {traceback.format_exc()}")
            raise ValueError(f"Failed to refresh access token: {str(e)}")

    @staticmethod
    def is_token_expired(token_data: Dict) -> bool:
        """
        Check if access token is expired.

        Args:
            token_data: Token response dictionary from exchange_code_for_token or refresh_access_token

        Returns:
            True if token is expired or expiring soon (within 5 minutes)
        """
        if "obtained_at" not in token_data or "expires_in" not in token_data:
            return True

        try:
            obtained_at = datetime.fromisoformat(token_data["obtained_at"])
            expires_in = token_data["expires_in"]
            expiration_time = obtained_at + timedelta(seconds=expires_in)
            # Consider expired if less than 5 minutes remaining
            return datetime.utcnow() >= (expiration_time - timedelta(minutes=5))
        except Exception as e:
            logger.warning(f"Could not determine token expiration: {str(e)}")
            return True

    @staticmethod
    def get_user_info(access_token: str, cloud_id: str) -> Dict:
        """
        Get authenticated user information using access token.

        Args:
            access_token: OAuth2 access token
            cloud_id: Confluence cloud site ID (from authorization response)

        Returns:
            User information dictionary
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }
            # Get user info from Atlassian API
            url = "https://api.atlassian.com/me"
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except Exception as e:
            logger.error(f"Error fetching user info: {traceback.format_exc()}")
            raise ValueError(f"Failed to fetch user information: {str(e)}")


class TokenManager:
    """
    Manages OAuth2 token storage and refresh logic.
    Uses a simple in-memory storage (can be extended to use database/file).
    """

    def __init__(self):
        self.tokens: Dict[str, Dict] = {}

    def store_token(self, key: str, token_data: Dict) -> None:
        """Store token data."""
        self.tokens[key] = token_data
        logger.info(f"Token stored for key: {key}")

    def get_token(self, key: str) -> Optional[Dict]:
        """Get stored token data."""
        return self.tokens.get(key)

    def get_valid_token(
        self,
        key: str,
        refresh_callback=None,
    ) -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.

        Args:
            key: Token identifier
            refresh_callback: Optional callback function(refresh_token) -> new_token_data

        Returns:
            Valid access token or None if unavailable
        """
        token_data = self.get_token(key)
        if not token_data:
            return None

        # Check if token is expired
        if ConfluenceOAuth2.is_token_expired(token_data):
            logger.info(f"Token expired for key: {key}, attempting refresh")

            # Try to refresh if we have a refresh token and callback
            if "refresh_token" in token_data and refresh_callback:
                try:
                    new_token_data = refresh_callback(token_data["refresh_token"])
                    self.store_token(key, new_token_data)
                    return new_token_data.get("access_token")
                except Exception as e:
                    logger.error(f"Failed to refresh token: {str(e)}")
                    return None

            return None

        return token_data.get("access_token")

    def delete_token(self, key: str) -> None:
        """Delete stored token."""
        if key in self.tokens:
            del self.tokens[key]
            logger.info(f"Token deleted for key: {key}")

    def clear_all(self) -> None:
        """Clear all stored tokens."""
        self.tokens.clear()
        logger.info("All tokens cleared")


def extract_cloud_id_from_response(token_response: Dict) -> Optional[str]:
    """
    Extract Confluence cloud site ID from token response.
    The cloud_id may be returned in different ways depending on Atlassian API.

    Args:
        token_response: Response from token exchange

    Returns:
        Cloud site ID or None
    """
    # Check various possible locations for cloud_id
    cloud_id = (
        token_response.get("cloud_id")
        or token_response.get("site_id")
        or token_response.get("resource_server_id")
    )
    return cloud_id
