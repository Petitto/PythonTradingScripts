import os
from dataclasses import dataclass
from typing import Dict, Optional
from urllib.parse import urlencode

import requests
from requests.auth import HTTPBasicAuth

from .token_manager import TokenManager


class OAuthError(Exception):
    """Raised when the OAuth flow cannot complete successfully."""


@dataclass
class OAuthConfig:
    client_id: str
    client_secret: Optional[str] = None
    redirect_uri: Optional[str] = None
    auth_url: Optional[str] = None
    token_url: Optional[str] = None
    token_file: Optional[str] = None
    scope: str = "readonly"
    response_type: str = "code"

    @classmethod
    def from_env(cls, prefix: str = "SCHWAB_") -> "OAuthConfig":
        return cls(
            client_id=os.getenv(f"{prefix}CLIENT_ID", ""),
            client_secret=os.getenv(f"{prefix}CLIENT_SECRET"),
            redirect_uri=os.getenv(f"{prefix}REDIRECT_URI"),
            auth_url=os.getenv(
                f"{prefix}AUTH_URL",
                "https://api.schwabapi.com/v1/oauth/authorize",
            ),
            token_url=os.getenv(
                f"{prefix}TOKEN_URL",
                "https://api.schwabapi.com/v1/oauth/token",
            ),
            token_file=os.getenv(f"{prefix}TOKEN_FILE"),
            scope=os.getenv(f"{prefix}SCOPE", "readonly"),
        )


class OAuthManager:
    def __init__(self, config: OAuthConfig, token_manager: Optional[TokenManager] = None):
        self.config = config
        self.token_manager = token_manager or TokenManager(config.token_file)

    def build_authorization_url(self, state: Optional[str] = None, code_challenge: Optional[str] = None) -> str:
        if not self.config.client_id:
            raise OAuthError("OAuth client_id is required")
        if not self.config.redirect_uri:
            raise OAuthError("OAuth redirect_uri is required")

        params = {
            "response_type": self.config.response_type,
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "scope": self.config.scope,
        }
        if state:
            params["state"] = state
        if code_challenge:
            params["code_challenge"] = code_challenge

        auth_url = self.config.auth_url or "https://api.schwab.com/v1/oauth/authorize"
        return f"{auth_url}?{urlencode(params)}"

    def _request_tokens(self, payload: Dict[str, str]) -> dict:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        auth = None
        if self.config.client_secret:
            auth = HTTPBasicAuth(self.config.client_id, self.config.client_secret)

        response = requests.post(
            self.config.token_url
            or "https://api.schwabapi.com/v1/oauth/token",
            data=payload,
            headers=headers,
            auth=auth,
            timeout=30,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            message = response.text.strip() or response.reason
            raise OAuthError(
                f"Token request failed {response.status_code}: {message}"
            ) from exc

        tokens = response.json()
        if not tokens.get("access_token"):
            raise OAuthError("OAuth token exchange did not return an access token")

        self.token_manager.save(tokens)
        return tokens

    def exchange_code_for_tokens(self, auth_code: str, state: Optional[str] = None, code_verifier: Optional[str] = None) -> dict:
        if not auth_code:
            raise OAuthError("Authorization code is required")

        payload = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.config.redirect_uri,
            "client_id": self.config.client_id,
        }
        if state:
            payload["state"] = state
        if code_verifier:
            payload["code_verifier"] = code_verifier

        return self._request_tokens(payload)

    def refresh_access_token(self) -> dict:
        tokens = self.token_manager.load()
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise OAuthError("A refresh token is required to refresh the access token")

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.config.client_id,
        }
        return self._request_tokens(payload)

    def get_access_token(self) -> str:
        tokens = self.token_manager.load()
        access_token = tokens.get("access_token")
        if not access_token:
            raise OAuthError("No access token is available")

        if self.token_manager.is_access_token_expired():
            tokens = self.refresh_access_token()
            access_token = tokens.get("access_token")

        return access_token

    def clear_tokens(self) -> None:
        self.token_manager.clear()
