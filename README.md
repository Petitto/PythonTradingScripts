# PythonTradingScripts

This project now includes a starter OAuth implementation for Schwab.

## OAuth setup

Set the following environment variables before running the example flow:

- SCHWAB_CLIENT_ID
- SCHWAB_CLIENT_SECRET (optional for some setups)
- SCHWAB_REDIRECT_URI
- SCHWAB_AUTH_URL (optional, defaults to Schwab's OAuth authorize endpoint)
- SCHWAB_TOKEN_URL (optional, defaults to Schwab's OAuth token endpoint)
- SCHWAB_TOKEN_FILE (optional, custom path for persisted tokens)
- SCHWAB_AUTH_CODE (set after completing the browser-based authorization step)

Example:

```bash
export SCHWAB_CLIENT_ID="your-client-id"
export SCHWAB_CLIENT_SECRET="your-client-secret"
export SCHWAB_REDIRECT_URI="https://127.0.0.1"
export SCHWAB_TOKEN_FILE="$HOME/.schwab_tokens.json"
python3 main.py
```

After you get the authorization code from the browser redirect, export it the same way:

```bash
export SCHWAB_AUTH_CODE="abc123def456"
python3 main.py
```

The script prints the authorization URL, which you can open in a browser.
After authorizing the app, Schwab redirects your browser to the configured `SCHWAB_REDIRECT_URI` with a query parameter named `code`.
Copy that value and set it as `SCHWAB_AUTH_CODE`, then run the script again to exchange the code for tokens.

> If you want automatic capture, use a local HTTP redirect URI such as `http://127.0.0.1:8000` and register that exact URI with Schwab.

For example, if the redirect URL looks like:

```text
https://127.0.0.1/?code=abc123def456&state=...
```

then use `abc123def456` as `SCHWAB_AUTH_CODE`.

> Note: the authorization code is single-use and short-lived. If you see a `400 Bad Request` from `https://api.schwab.com/v1/oauth/token`, the most common causes are:
> - the code was already exchanged once
> - the code expired before use
> - `SCHWAB_REDIRECT_URI` does not exactly match the URI registered with Schwab

If that happens, rerun `python3 main.py`, open the authorization URL again, get a fresh `code` from the redirect URL, export it, and retry.

> Ensure that `SCHWAB_REDIRECT_URI` exactly matches the redirect URI registered in your Schwab app settings, including the scheme, host, port, and any trailing slash.

### Notes on running the project

- The local run flow has not changed significantly: you still call `python3 main.py` and use `SCHWAB_AUTH_CODE` for the second step.
- The only new runtime option is `SCHWAB_TOKEN_FILE`, which lets you choose where the token cache is stored.
- If you later use `api/schwab_client.py`, you can also set `SCHWAB_API_BASE_URL` to override the default Schwab API base URL.

## Running tests

```bash
python3 -m unittest discover -s tests -v
```