import io
import os
from dotenv import load_dotenv

import docx
from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from database import Base, engine
from dependencies import require_role
import admin_routes
import auth_routes
import chat_routes
import conversation_routes
import models

# Load environment variables
load_dotenv()

app = FastAPI()
Base.metadata.create_all(bind=engine)

# ============================================================
# CORS CONFIGURATION - UPDATED FOR VERCEL
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "null",
        "*",
        # Add your Vercel frontend URL here after deployment
        "https://datamart-chatbot.vercel.app",
        "https://datamart-chatbot-1978.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(chat_routes.router)
app.include_router(admin_routes.router)
app.include_router(conversation_routes.router)

@app.get("/")
def root():
    return {"message": "Datamart chatbot backend is running"}

@app.get("/test-db")
def test_db():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        return {"db_test_result": result.scalar()}

@app.get("/admin-only")
def admin_only(current_user=Depends(require_role("admin"))):
    return {"message": "Welcome admin"}

@app.post("/extract-docx")
async def extract_docx(file: UploadFile = File(...)):
    contents = await file.read()
    doc = docx.Document(io.BytesIO(contents))
    text_content = "\n".join(para.text for para in doc.paragraphs)
    return {"text": text_content}