import json
import os
import time
from typing import Optional


class TokenManager:
    def __init__(self, token_file: Optional[str] = None):
        self.token_file = token_file or os.path.join(os.getcwd(), ".tokens.json")

    def save(self, tokens: dict) -> None:
        payload = dict(tokens)
        expires_at = payload.get("expires_at")
        if not expires_at and payload.get("expires_in"):
            expires_at = int(time.time()) + int(payload["expires_in"])
            payload["expires_at"] = expires_at

        with open(self.token_file, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def load(self) -> dict:
        if not os.path.exists(self.token_file):
            return {}

        with open(self.token_file, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def clear(self) -> None:
        if os.path.exists(self.token_file):
            os.remove(self.token_file)

    def is_access_token_expired(self, buffer_seconds: int = 60) -> bool:
        tokens = self.load()
        expires_at = tokens.get("expires_at")
        if not expires_at:
            return True
        return int(time.time()) >= int(expires_at) - buffer_seconds
