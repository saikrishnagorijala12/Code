import os
from flask import url_for
from msal import ConfidentialClientApplication


CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")
TENANT_ID = os.environ.get("TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
REDIRECT_PATH = "/getAToken"
SCOPE = ["User.Read"]

def _build_msal_app(cache=None):
    return ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=CLIENT_SECRET,
        token_cache=cache
    )


def _build_auth_url(state=None):
    return _build_msal_app().get_authorization_request_url(
        SCOPE,
        state=state,
        redirect_uri=url_for("auth.authorized", _external=True)  
    )