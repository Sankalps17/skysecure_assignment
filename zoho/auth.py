"""Zoho OAuth 2.0 helpers — URL construction, code exchange, and token refresh."""

import time
from urllib.parse import urlencode

import requests

from config import (
    ZOHO_CLIENT_ID,
    ZOHO_CLIENT_SECRET,
    ZOHO_DOMAIN,
    ZOHO_REDIRECT_URI,
    ZOHO_SCOPES,
    logger,
)
from zoho.models import ZohoTokens


def build_auth_url() -> str:
    """Construct the Zoho OAuth authorization URL for browser redirect."""
    base = f"https://accounts.zoho{ZOHO_DOMAIN}/oauth/v2/auth"
    params = {
        "scope": ",".join(ZOHO_SCOPES),
        "client_id": ZOHO_CLIENT_ID,
        "response_type": "code",
        "access_type": "offline",
        "redirect_uri": ZOHO_REDIRECT_URI,
        "prompt": "consent",
    }
    return f"{base}?{urlencode(params)}"


def exchange_code(code: str, domain: str = "") -> ZohoTokens:
    """Exchange a one-time authorization code for access + refresh tokens.

    Args:
        code: The authorization code from the OAuth callback.
        domain: Zoho domain suffix (e.g. ".in", ".com"). Defaults to ZOHO_DOMAIN from .env.
    """
    effective_domain = domain or ZOHO_DOMAIN
    url = f"https://accounts.zoho{effective_domain}/oauth/v2/token"
    resp = requests.post(url, data={
        "grant_type": "authorization_code",
        "client_id": ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "redirect_uri": ZOHO_REDIRECT_URI,
        "code": code,
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        desc = data.get("error_description", data["error"])
        raise ValueError(f"Zoho OAuth error: {desc}")

    logger.info("Zoho tokens obtained via authorization code (domain: %s)", effective_domain)
    return ZohoTokens(
        access_token=data["access_token"],
        refresh_token=data["refresh_token"],
        expires_at=time.time() + data.get("expires_in", 3600) - 60,
    )


def refresh_access_token(current_refresh_token: str, domain: str = "") -> ZohoTokens:
    """Use a refresh token to obtain a new access token.

    Args:
        current_refresh_token: The refresh token to exchange.
        domain: Zoho domain suffix (e.g. ".in", ".com"). Defaults to ZOHO_DOMAIN from .env.
    """
    effective_domain = domain or ZOHO_DOMAIN
    url = f"https://accounts.zoho{effective_domain}/oauth/v2/token"
    resp = requests.post(url, data={
        "grant_type": "refresh_token",
        "client_id": ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "refresh_token": current_refresh_token,
    }, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        desc = data.get("error_description", data["error"])
        raise ValueError(f"Zoho token refresh error: {desc}")

    logger.info("Zoho access token refreshed (domain: %s)", effective_domain)
    return ZohoTokens(
        access_token=data["access_token"],
        refresh_token=current_refresh_token,  # Refresh token stays the same
        expires_at=time.time() + data.get("expires_in", 3600) - 60,
    )
