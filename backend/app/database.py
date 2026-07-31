# backend/app/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env.local
env_path = Path(__file__).parent.parent.parent / ".env.local"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print("✅ Loaded .env.local")
else:
    load_dotenv()
    print("⚠️ No .env.local found, trying default")

# Get database URL - try multiple possible variable names
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DATABASE_URL = os.getenv("POSTGRES_URL")

if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./app.db"
    print("⚠️ No DATABASE_URL found, using SQLite")
else:
    print("✅ Using PostgreSQL")

# Create engine
# Validate pooled connections before every use so expired PostgreSQL/Neon
# SSL connections are replaced instead of causing 500 errors.
engine_options = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
else:
    engine_options.update(
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
    )

engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()