import io
import os
from dotenv import load_dotenv
import docx
from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

# Local imports - all from app/
from app.database import Base, engine
from app.dependencies import require_role
from app.routes import auth_routes, chat_routes, admin_routes, conversation_routes
from app.routes.chat import router as lead_chat_router
from app.routes.admin.leads import router as admin_leads_router
import app.models

load_dotenv()

app = FastAPI()
Base.metadata.create_all(bind=engine)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_routes.router)
app.include_router(chat_routes.router)
app.include_router(admin_routes.router)
app.include_router(conversation_routes.router)
app.include_router(lead_chat_router, prefix="/api")
app.include_router(admin_leads_router, prefix="/api")

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