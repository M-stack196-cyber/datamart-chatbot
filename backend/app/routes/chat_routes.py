import os

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user
from app.models import User
from app.schemas import ChatRequest

load_dotenv()

router = APIRouter(tags=["chat"])


@router.post("/chat")
def chat_proxy(payload: ChatRequest, current_user: User = Depends(get_current_user)):
    webhook_url = os.getenv("N8N_CHAT_WEBHOOK_URL")
    if not webhook_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server chat webhook is not configured",
        )

    request_payload = {
        "question": payload.question,
        "user_role": current_user.role,
    }

    try:
        response = requests.post(webhook_url, json=request_payload, timeout=45)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream chat workflow failed: {exc}",
        ) from exc

    try:
        return response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upstream chat workflow returned invalid JSON",
        ) from exc