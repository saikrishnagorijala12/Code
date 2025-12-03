import time
import json
import requests
from threading import Lock
from flask import session, current_app


with open("domo.json", "r") as f:
    domo_user_map = json.load(f)


_token_cache = {}
_token_lock = Lock()


def _get_config():
    """Base app config (non-secret values). Keep client_id/secret as fallback only."""
    cfg = current_app.config
    return {
        "api_host": cfg.get("DOMO_API_HOST"),
        "embed_host": cfg.get("DOMO_EMBED_HOST"),
        "card_target": cfg.get("CARD_DASHBOARD", "cards"),
        "fallback_client_id": cfg.get("DOMO_CLIENT_ID"),
        "fallback_client_secret": cfg.get("DOMO_CLIENT_SECRET"),
    }


def _find_domo_entry_by_email(email: str):
    """Return the first matching domo.json entry for the given email, or None."""
    if not email:
        return None
    for entry in domo_user_map:
        if entry.get("email") and entry.get("email").lower() == email.lower():
            return entry
    return None


def _get_client_credentials_for_session():
    """
    Determine client_id and client_secret to use for the current user session.
    Priority:
     1) domo.json entry matching session user's email
     2) fallback values from Flask config
    Raises ValueError if no client_id available.
    """
    cfg = _get_config()
    user = session.get("user")
    if user:
        email = user.get("preferred_username") or user.get("email")
        entry = _find_domo_entry_by_email(email)
        if entry:
            client_id = entry.get("DOMO_CLIENT_ID") or entry.get("client_id") or entry.get("DOMO_CLIENTID")
            client_secret = entry.get("DOMO_CLIENT_SECRET") or entry.get("client_secret") or entry.get("DOMO_CLIENTSECRET")
            if client_id:
                return client_id, client_secret

    if cfg["fallback_client_id"]:
        return cfg["fallback_client_id"], cfg["fallback_client_secret"]

    raise ValueError("No DOMO client_id available for current session")


def get_access_token(scopes: str = "data user dashboard"):
    """
    Acquire a DOMO access token using the client credentials for the current session user.
    Caches tokens per-client_id to avoid collisions when multiple client credentials are used.
    """
    client_id, client_secret = _get_client_credentials_for_session()
    now = time.time()
    cache_key = client_id

    with _token_lock:
        cached = _token_cache.get(cache_key)
        if cached and cached.get("access_token") and cached.get("expires_at", 0) > now + 5:
            return cached["access_token"]

    cfg = _get_config()
    token_url = f"{cfg['api_host'].rstrip('/')}/oauth/token"

    if not client_id or not client_secret:
        raise ValueError("Missing client_secret for DOMO client_id: %s" % client_id)

    response = requests.post(
        token_url,
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials", "scope": scopes},
        headers={"Accept": "application/json"},
        timeout=10
    )
    response.raise_for_status()

    data = response.json()
    access_token = data["access_token"]
    expires_in = int(data.get("expires_in", 300))
    expires_at = now + expires_in

    with _token_lock:
        _token_cache[cache_key] = {"access_token": access_token, "expires_at": expires_at}

    return access_token


def create_embed_token(access_token, embed_id, session_minutes=60):
    if not embed_id:
        raise ValueError("embed_id is required")

    cfg = _get_config()
    url = f"{cfg['api_host'].rstrip('/')}/v1/{cfg['card_target']}/embed/auth"
    payload = {
        "sessionLength": session_minutes * 60,
        "authorizations": [
            {
                "token": embed_id,
                "permissions": ["READ", "FILTER", "EXPORT"],
                "filters": []
            }
        ]
    }

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        json=payload,
        timeout=10
    )

    response.raise_for_status()
    return response.json().get("authentication")


def get_embed_ids_for_user():
    """Return list of embed_ids the signed-in user is allowed to access (from domo.json)."""
    user = session.get("user")
    if not user:
        return []

    email = user.get("preferred_username") or user.get("email")
    return [entry["embed_id"] for entry in domo_user_map if entry.get("email", "").lower() == (email or "").lower()]


def is_logged_in():
    return "user" in session


def get_embed_configuration():
    """
    Returns:
      - tokens: list of {"id": embed_id, "token": authentication_token}
      - embed_host: URL to use in the frontend to embed DOMO cards/dashboards
    """
    cfg = _get_config()
    embed_ids = get_embed_ids_for_user()
    if not embed_ids:
        return None

    access = get_access_token()
    tokens = [{"id": eid, "token": create_embed_token(access, eid)} for eid in embed_ids]

    return tokens, cfg["embed_host"]
