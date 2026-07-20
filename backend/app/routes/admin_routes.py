import os
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models import DOCUMENT_VISIBILITY, Document, USER_ROLES, User
from app.schemas import (
    DocumentResponse,
    DocumentStatusUpdate,
    SimpleMessageResponse,
    UserAdminResponse,
    UserRoleUpdate,
    UserStatusUpdate,
)

load_dotenv()

router = APIRouter(prefix="/admin", tags=["admin"])

INTERNAL_WEBHOOK_SECRET = os.getenv("INTERNAL_WEBHOOK_SECRET")


def _delete_document_vectors(doc_id: int) -> None:
    api_key = os.getenv("PINECONE_API_KEY")
    index_host = os.getenv("PINECONE_INDEX_HOST")
    namespace = os.getenv("PINECONE_NAMESPACE")

    if not api_key or not index_host:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Pinecone deletion is not configured",
        )

    index_host = index_host.replace("https://", "").replace("http://", "")
    url = f"https://{index_host}/vectors/delete"
    body = {
        "deleteAll": False,
        "filter": {"doc_id": {"$eq": str(doc_id)}},
    }
    if namespace:
        body["namespace"] = namespace

    headers = {
        "Api-Key": api_key,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(url, json=body, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to delete vectors from Pinecone: {exc}",
        ) from exc


@router.post("/upload")
def upload_document_proxy(
    title: str = Form(...),
    visibility: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    if visibility not in DOCUMENT_VISIBILITY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid visibility")

    webhook_url = os.getenv("N8N_UPLOAD_WEBHOOK_URL")
    if not webhook_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server upload webhook is not configured",
        )

    document = Document(
        title=title,
        filename=file.filename,
        content_type=file.content_type,
        visibility=visibility,
        uploaded_by=current_user.id,
        status="processing",
        chunk_count=0,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    file_bytes = file.file.read()
    files = {
        "file": (file.filename, file_bytes, file.content_type or "application/octet-stream"),
    }
    data = {
        "title": title,
        "visibility": visibility,
        "uploaded_by": str(current_user.id),
        "document_id": str(document.id),
    }

    try:
        response = requests.post(webhook_url, files=files, data=data, timeout=120)
        response.raise_for_status()
    except requests.RequestException as exc:
        document.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upload workflow failed: {exc}",
        ) from exc

    try:
        workflow_response = response.json()
    except ValueError:
        workflow_response = {"message": "Upload accepted by workflow"}

    workflow_response["document_id"] = document.id
    return workflow_response


@router.patch("/documents/{document_id}/status", response_model=DocumentResponse)
def update_document_status(
    document_id: int,
    payload: DocumentStatusUpdate,
    x_internal_secret: str | None = None,
    db: Session = Depends(get_db),
):
    if INTERNAL_WEBHOOK_SECRET and x_internal_secret != INTERNAL_WEBHOOK_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal secret")

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    document.status = payload.status
    document.chunk_count = payload.chunk_count
    db.commit()
    db.refresh(document)
    return document


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role("admin")),
):
    return db.query(Document).order_by(Document.created_at.desc()).all()


@router.delete("/documents/{document_id}", response_model=SimpleMessageResponse)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role("admin")),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    _delete_document_vectors(document.id)
    db.delete(document)
    db.commit()
    return {"message": "Document and vectors deleted"}


@router.get("/users", response_model=list[UserAdminResponse])
def list_users(
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role("admin")),
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.patch("/users/{user_id}/role", response_model=UserAdminResponse)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role("admin")),
):
    if payload.role not in USER_ROLES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/status", response_model=UserAdminResponse)
def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role("admin")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return user