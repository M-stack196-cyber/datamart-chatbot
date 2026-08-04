import os
import secrets
from pathlib import Path

from dotenv import dotenv_values, set_key
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from google_auth_oauthlib.flow import Flow


router = APIRouter(prefix="/google-calendar", tags=["Google Calendar"])

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/calendar.events.freebusy",
]


def _env_file() -> Path:
    return Path(__file__).resolve().parents[3] / ".env.local"


def _client_config() -> dict:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/google-calendar/callback",
    )

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth credentials are not configured",
        )

    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }


def _create_flow(
    state: str | None = None,
    code_verifier: str | None = None,
) -> Flow:
    redirect_uri = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/google-calendar/callback",
    )

    flow = Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        state=state,
        code_verifier=code_verifier,
        autogenerate_code_verifier=False,
    )
    flow.redirect_uri = redirect_uri
    return flow


@router.get("/status")
def google_calendar_status():
    return {
        "configured": bool(
            os.getenv("GOOGLE_CLIENT_ID")
            and os.getenv("GOOGLE_CLIENT_SECRET")
        ),
        "authorized": bool(os.getenv("GOOGLE_REFRESH_TOKEN")),
        "calendar_id": os.getenv(
            "GOOGLE_CALENDAR_ID",
            "incdatamart@gmail.com",
        ),
        "timezone": os.getenv(
            "GOOGLE_CALENDAR_TIMEZONE",
            "Asia/Karachi",
        ),
    }


@router.get("/authorize")
def google_calendar_authorize():
    state = secrets.token_urlsafe(32)
    code_verifier = secrets.token_urlsafe(64)

    set_key(
        str(_env_file()),
        "GOOGLE_OAUTH_STATE",
        state,
        quote_mode="always",
    )
    os.environ["GOOGLE_OAUTH_STATE"] = state

    set_key(
        str(_env_file()),
        "GOOGLE_CODE_VERIFIER",
        code_verifier,
        quote_mode="always",
    )
    os.environ["GOOGLE_CODE_VERIFIER"] = code_verifier

    flow = _create_flow(
        state=state,
        code_verifier=code_verifier,
    )

    authorization_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
        login_hint="incdatamart@gmail.com",
    )

    return RedirectResponse(authorization_url)


@router.get("/callback", response_class=HTMLResponse)
def google_calendar_callback(
    code: str = Query(...),
    state: str = Query(...),
):
    expected_state = (
        os.getenv("GOOGLE_OAUTH_STATE")
        or dotenv_values(_env_file()).get("GOOGLE_OAUTH_STATE")
    )

    if not expected_state or not secrets.compare_digest(
        state,
        expected_state,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid Google OAuth state",
        )

    code_verifier = (
        os.getenv("GOOGLE_CODE_VERIFIER")
        or dotenv_values(_env_file()).get("GOOGLE_CODE_VERIFIER")
    )

    if not code_verifier:
        raise HTTPException(
            status_code=400,
            detail="Missing Google OAuth code verifier",
        )

    flow = _create_flow(
        state=state,
        code_verifier=code_verifier,
    )

    try:
        flow.fetch_token(code=code)
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=f"Google authorization failed: {error}",
        ) from error

    refresh_token = flow.credentials.refresh_token

    if not refresh_token:
        raise HTTPException(
            status_code=400,
            detail=(
                "Google did not return a refresh token. "
                "Revoke the app access and authorize again."
            ),
        )

    set_key(
        str(_env_file()),
        "GOOGLE_REFRESH_TOKEN",
        refresh_token,
        quote_mode="always",
    )

    return HTMLResponse(
        """
        <html>
          <body style="font-family:Arial;padding:40px">
            <h2>Google Calendar connected successfully</h2>
            <p>The refresh token was saved securely.</p>
            <p>You can close this browser tab.</p>
          </body>
        </html>
        """
    )
