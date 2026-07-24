# migrate_db.py
from app.database import engine
from app.models import Base
from sqlalchemy import inspect

def migrate_database():
    """Create or update database tables."""
    print("🔄 Starting database migration...")
    
    # Check existing tables
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    print(f"📋 Existing tables: {', '.join(existing_tables) if existing_tables else 'None'}")
    
    # Create/update tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables updated successfully!")
    
    # Verify new tables
    inspector = inspect(engine)
    new_tables = inspector.get_table_names()
    print(f"📋 Tables now available: {', '.join(new_tables)}")
    
    # Check specific tables
    tables_to_check = ['users', 'contact_info', 'conversation_history', 'project_requests', 'project_conversation']
    for table in tables_to_check:
        if table in new_tables:
            columns = inspector.get_columns(table)
            print(f"✅ {table} table has {len(columns)} columns")
        else:
            print(f"⚠️ {table} table not found")

if __name__ == "__main__":
    migrate_database()
