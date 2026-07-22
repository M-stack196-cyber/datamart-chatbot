import io
import os
from dotenv import load_dotenv
import docx
from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import Base, engine
from app.dependencies import require_role
from app.routes import auth_routes, chat_routes, admin_routes, conversation_routes
from app.routes.chat import router as lead_chat_router
from app.routes.admin.leads import router as admin_leads_router
from app.routes.admin_ui import router as admin_ui_router
import app.models

load_dotenv()

app = FastAPI()

# Create database tables
Base.metadata.create_all(bind=engine)

# ============================================================
# CORS Configuration - Allow Frontend to Access Backend
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://datamart-chatbot.vercel.app",
        "https://datamart-chatbot.vercel.app/",
        "https://datamart-backend.vercel.app",
        "https://datamart-backend.vercel.app/",
        "http://localhost:3000",
        "http://localhost:8000",
        "https://datamart-chatbot-l978.vercel.app",
        "https://datamart-chatbot-l978.vercel.app/",
        "https://datamart-chatbot-l978-7puzleryj-m-stack196-cybers-projects.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "Accept",
        "Origin",
        "X-Requested-With",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
    expose_headers=[
        "Content-Type",
        "Authorization",
    ],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# ============================================================
# Include All Routes
# ============================================================
app.include_router(auth_routes.router, prefix="/api")
app.include_router(chat_routes.router, prefix="/api")
app.include_router(admin_routes.router, prefix="/api")
app.include_router(conversation_routes.router, prefix="/api")
app.include_router(lead_chat_router, prefix="/api")
app.include_router(admin_leads_router, prefix="/api")
app.include_router(admin_ui_router)

# ============================================================
# Health Check Endpoints
# ============================================================
@app.get("/")
def root():
    return {"message": "Datamart chatbot backend is running"}

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "cors_enabled": True,
        "allowed_origins": [
            "https://datamart-chatbot.vercel.app",
            "https://datamart-backend.vercel.app",
            "http://localhost:3000",
            "http://localhost:8000"
        ]
    }

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

# ============================================================
# OPTIONS Endpoint for CORS Preflight (Fallback)
# ============================================================
from fastapi import Response

@app.options("/{path:path}")
async def options_handler():
    """Handle OPTIONS requests for CORS preflight"""
    response = Response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, PATCH, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, Origin, X-Requested-With"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Max-Age"] = "600"
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)