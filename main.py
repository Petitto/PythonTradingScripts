import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from auth.oauth import OAuthConfig, OAuthError, OAuthManager


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed_path = urlparse(self.path)
        query = parse_qs(parsed_path.query)
        code = query.get("code", [None])[0]

        if code:
            self.server.auth_code = code
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Authorization complete</h1><p>You may now return to the terminal.</p></body></html>"
            )
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Missing authorization code</h1></body></html>"
            )

    def log_message(self, format: str, *args: object) -> None:
        return


def capture_auth_code_via_local_server(redirect_uri: str, auth_url: str, timeout_seconds: int = 300) -> str:
    parsed = urlparse(redirect_uri)
    if parsed.scheme != "http":
        raise OAuthError(
            "Local callback capture requires an http:// redirect URI. "
            "Use a local HTTP redirect URI like http://127.0.0.1:8000 "
            "and register it with Schwab."
        )

    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80
    server_address = (host, port)

    try:
        httpd = ThreadingHTTPServer(server_address, OAuthCallbackHandler)
    except OSError as exc:
        raise OAuthError(
            f"Could not start local callback server on {host}:{port}: {exc}. "
            "Choose a free port and use an http:// redirect URI."
        ) from exc
    httpd.auth_code = None

    print("Open this URL to authorize your Schwab app:")
    print(auth_url)
    try:
        webbrowser.open(auth_url)
    except Exception:
        pass

    def run_server() -> None:
        httpd.serve_forever()

    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()

    print(f"Waiting for Schwab to redirect to {redirect_uri}...")
    elapsed = 0
    while elapsed < timeout_seconds and httpd.auth_code is None:
        thread.join(timeout=0.5)
        elapsed += 0.5

    httpd.shutdown()
    thread.join(timeout=1)

    if not httpd.auth_code:
        raise OAuthError(
            "No authorization code received. Confirm the redirect URI is registered and open the authorization URL again."
        )

    return httpd.auth_code


def main() -> None:
    config = OAuthConfig.from_env()
    manager = OAuthManager(config)

    if not config.client_id:
        print("Set SCHWAB_CLIENT_ID and SCHWAB_REDIRECT_URI before starting OAuth")
        return

    auth_url = manager.build_authorization_url()
    auth_code = os.getenv("SCHWAB_AUTH_CODE")
    auto_capture = os.getenv("SCHWAB_AUTO_CAPTURE", "false").lower() in ("1", "true", "yes")

    print("Open this URL to authorize your Schwab app:")
    print(auth_url)

    if not auth_code:
        if auto_capture:
            try:
                auth_code = capture_auth_code_via_local_server(config.redirect_uri, auth_url)
            except OAuthError as exc:
                print(f"OAuth exchange failed: {exc}")
                return
        else:
            print("After authorizing the app, copy the `code` value from the redirect URL.")
            print("Then set SCHWAB_AUTH_CODE and run the script again.")
            return

    try:
        tokens = manager.exchange_code_for_tokens(auth_code)
    except OAuthError as exc:
        print(f"OAuth exchange failed: {exc}")
        return

    print("Tokens stored successfully")
    print(tokens)


if __name__ == "__main__":
    main()
