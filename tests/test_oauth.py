import os
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from auth.oauth import OAuthConfig, OAuthError, OAuthManager
from auth.token_manager import TokenManager


class TokenManagerTests(unittest.TestCase):
    def test_save_and_load_tokens(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = os.path.join(tmpdir, "tokens.json")
            manager = TokenManager(token_file)
            payload = {
                "access_token": "access-123",
                "refresh_token": "refresh-456",
                "expires_in": 3600,
            }

            manager.save(payload)
            self.assertEqual(manager.load(), payload)

    def test_detects_expired_access_token(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            token_file = os.path.join(tmpdir, "tokens.json")
            manager = TokenManager(token_file)
            manager.save({"access_token": "access-123", "expires_at": int(time.time()) - 10})

            self.assertTrue(manager.is_access_token_expired())


class OAuthManagerTests(unittest.TestCase):
    def test_build_authorization_url_contains_required_parameters(self):
        config = OAuthConfig(
            client_id="demo-client",
            redirect_uri="https://example.com/callback",
            auth_url="https://api.schwab.com/v1/oauth/authorize",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = OAuthManager(config, TokenManager(os.path.join(tmpdir, "tokens.json")))
            url = manager.build_authorization_url(state="abc123")

            self.assertIn("response_type=code", url)
            self.assertIn("client_id=demo-client", url)
            self.assertIn("redirect_uri=https%3A%2F%2Fexample.com%2Fcallback", url)
            self.assertIn("state=abc123", url)
            self.assertIn("scope=readonly", url)

    def test_exchange_code_for_tokens_persists_tokens(self):
        config = OAuthConfig(
            client_id="demo-client",
            redirect_uri="https://example.com/callback",
            token_url="https://api.schwab.com/v1/oauth/token",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            token_manager = TokenManager(os.path.join(tmpdir, "tokens.json"))
            manager = OAuthManager(config, token_manager)

            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = {
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "expires_in": 1800,
            }

            with patch("auth.oauth.requests.post", return_value=mock_response) as mock_post:
                tokens = manager.exchange_code_for_tokens("auth-code", "state", code_verifier="verifier")

            self.assertEqual(tokens["access_token"], "new-access")
            self.assertEqual(token_manager.load()["access_token"], "new-access")
            mock_post.assert_called_once()

    def test_refresh_requires_refresh_token(self):
        config = OAuthConfig(client_id="demo-client")
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = OAuthManager(config, TokenManager(os.path.join(tmpdir, "tokens.json")))

            with self.assertRaises(OAuthError):
                manager.refresh_access_token()
