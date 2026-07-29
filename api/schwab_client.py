import os
from typing import Any, Dict, Optional

import requests

from auth.oauth import OAuthConfig, OAuthError, OAuthManager


class SchwabClient:
    def __init__(self, config: Optional[OAuthConfig] = None, token_file: Optional[str] = None):
        self.config = config or OAuthConfig.from_env()
        if token_file:
            self.config.token_file = token_file
        self.oauth = OAuthManager(self.config)
        self.base_url = os.getenv("SCHWAB_API_BASE_URL", "https://api.schwabapi.com/trader/v1")

    def _headers(self) -> Dict[str, str]:
        access_token = self.oauth.get_access_token()
        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> Dict[str, Any]:
        url = f"{self.base_url}/{endpoint.lstrip('/') }"
        response = requests.request(method, url, headers=self._headers(), timeout=30, **kwargs)
        response.raise_for_status()
        return response.json()

    def get_accounts(self) -> Dict[str, Any]:
        return self._request("GET", "accounts")

    def get_positions(self) -> Dict[str, Any]:
        return self._request("GET", "positions")

    def get_quotes(self, symbols: Optional[list[str]] = None) -> Dict[str, Any]:
        params = {"symbols": ",".join(symbols)} if symbols else {}
        return self._request("GET", "quotes", params=params)

    def place_order(self, order_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "orders", json=order_payload)
