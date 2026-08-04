import io
import os
from dotenv import load_dotenv
import docx
from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import text

from app.database import Base, engine
from app.dependencies import require_role
from app.routes import auth_routes, admin_routes, conversation_routes
from app.routes.chat import router as lead_chat_router
from app.routes.google_calendar import router as google_calendar_router
from app.routes.meeting_reminders import router as meeting_reminders_router
from app.routes.admin.leads import router as admin_leads_router
from app.routes.admin.handoff import router as admin_handoff_router
from app.routes.admin.delete import router as admin_delete_router
from app.routes.admin_ui import router as admin_ui_router
import app.models

load_dotenv()

app = FastAPI()

# Create database tables
Base.metadata.create_all(bind=engine)
from app.runtime_schema import ensure_runtime_schema
ensure_runtime_schema(engine)

# ============================================================
# CORS Configuration - Explicitly Allow Frontend Ports
# ============================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # React Vite Frontend
        "http://localhost:8000",  # Backend itself
        "http://127.0.0.1:5173", 
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"], # <--- CRITICAL for widget compatibility
)

# ============================================================
# Include All Routes
# ============================================================
app.include_router(auth_routes.router, prefix="/api")
app.include_router(admin_routes.router, prefix="/api")
app.include_router(conversation_routes.router, prefix="/api")
app.include_router(lead_chat_router, prefix="/api")
app.include_router(google_calendar_router, prefix="/api")
app.include_router(meeting_reminders_router, prefix="/api")
app.include_router(admin_leads_router, prefix="/api")
app.include_router(admin_handoff_router, prefix="/api")
app.include_router(admin_delete_router, prefix="/api")
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
        "allowed_origins": ["http://localhost:5173", "http://localhost:8000"]
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
# Serve the Public Chat Widget (dtmindex.html)
# ============================================================
@app.get("/dtmindex.html", response_class=HTMLResponse)
async def serve_chat_widget():
    # Look for the file in the frontend/public folder
    file_path = os.path.join(os.path.dirname(__file__), "dtmindex.html")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return HTMLResponse(
            content=f"<h1>Error: dtmindex.html not found at {file_path}</h1>", 
            status_code=404
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)