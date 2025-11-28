import os, requests
from threading import Lock
import time

DOMO_API_HOST = os.getenv("DOMO_API_HOST")
DOMO_EMBED_HOST = os.getenv("DOMO_EMBED_HOST")
DOMO_CLIENT_ID = os.getenv("DOMO_CLIENT_ID")
DOMO_CLIENT_SECRET = os.getenv("DOMO_CLIENT_SECRET")
CARD_DASHBORD=os.getenv("C_D")

# Optional: provide default embed page ids per user (or from env)
EMBED_PAGE_ID_1 = os.getenv("EMBED_PAGE_ID_1")  # used for specific user
EMBED_PAGE_ID_2 = os.getenv("EMBED_PAGE_ID_2")  

# required = {
#     "DOMO_CLIENT_ID": DOMO_CLIENT_ID,
#     "DOMO_CLIENT_SECRET": DOMO_CLIENT_SECRET,
# }
# missing = [k for k, v in required.items() if not v]
# if missing:
#     raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

DOMO_TOKEN_CACHE = {"access_token": None, "expires_at": 0}
_DOMO_TOKEN_LOCK = Lock()

def get_domo_access_token(scopes: str = "data user dashboard"):
    """
    Request Domo OAuth token using client_credentials.
    Process-memory cache. Use Redis or similar in production.
    """
    now = time.time()
    with _DOMO_TOKEN_LOCK:
        if DOMO_TOKEN_CACHE["access_token"] and DOMO_TOKEN_CACHE["expires_at"] > now + 5:
            return DOMO_TOKEN_CACHE["access_token"]

        token_url = f"{DOMO_API_HOST}/oauth/token"
        auth = (DOMO_CLIENT_ID, DOMO_CLIENT_SECRET)
        headers = {"Accept": "application/json"}
        data = {"grant_type": "client_credentials", "scope": scopes}

        r = requests.post(token_url, auth=auth, data=data, headers=headers, timeout=10)
        r.raise_for_status()
        j = r.json()
        access_token = j.get("access_token")
        expires_in = int(j.get("expires_in", 300))

        DOMO_TOKEN_CACHE["access_token"] = access_token
        DOMO_TOKEN_CACHE["expires_at"] = time.time() + expires_in
        return access_token


def create_domo_embed_token(access_token: str, embed_id: str, session_length_minutes: int = 60):
    """
    Request an embed token from the Domo API.
    Make sure embed_id is valid and the Domo client has access.
    """
    if not embed_id:
        raise ValueError("embed_id is required")

    embed_token_url = f"{DOMO_API_HOST}/v1/{CARD_DASHBORD}/embed/auth"
    payload = {
        "sessionLength": session_length_minutes * 60,
        "authorizations": [
            {
                "token": embed_id,
                "permissions": ["READ", "FILTER", "EXPORT"],
                "filters": []
            }
        ]
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    r = requests.post(embed_token_url, headers=headers, json=payload, timeout=10)
    r.raise_for_status()
    return r.json().get("authentication")

def domo_create_user(access_token: str, email: str, first_name: str = "", last_name: str = "", role: str = "Participant"):
    """
    Example helper to create a user in Domo via API.
    NOTE: check Domo Admin API docs for exact payload and endpoint.
    This is a template showing how you'd call the users API.
    """
    # TODO: adjust endpoint/payload per Domo docs if different
    users_endpoint = f"{DOMO_API_HOST}/v1/users"  # verify from Domo docs
    payload = {
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
        "role": role,  # role name or id depending on API
        # other fields (status, groups, etc) as needed
    }
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    r = requests.post(users_endpoint, headers=headers, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()

def choose_embed_page_for_user(user):
    """
    Return the embed page id to use for this user.
    Replace this logic with your real mapping (DB, roles, groups, etc).
    """
    if not user:
        return EMBED_PAGE_ID_2 or EMBED_PAGE_ID_1
    if user.get("name") == "Rohith":
        return EMBED_PAGE_ID_1 or EMBED_PAGE_ID_2
    return EMBED_PAGE_ID_2



def is_logged_in():
    return "user" 
