"""
Database migration script to convert conversation_id columns from text to UUID.
Run this script once after making the model changes.
"""

import os
import sys
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env.local")
    sys.exit(1)

# Create engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def migrate_conversation_ids():
    """Convert text conversation_ids to UUID where possible."""
    
    print("🔄 Starting migration of conversation_id columns...")
    
    # List of tables and columns to migrate
    tables = [
        ("conversation_history", "conversation_id"),
        ("contact_info", "conversation_id"),
        ("conversation_state", "conversation_id"),
    ]
    
    for table_name, column_name in tables:
        print(f"\n📋 Processing {table_name}.{column_name}...")
        
        try:
            # Step 1: Check if column exists and is text type
            check_query = text("""
                SELECT data_type 
                FROM information_schema.columns 
                WHERE table_name = :table_name 
                AND column_name = :column_name
            """)
            result = db.execute(check_query, {"table_name": table_name, "column_name": column_name}).first()
            
            if not result:
                print(f"   ⚠️ Column {column_name} not found in {table_name}, skipping...")
                continue
                
            current_type = result[0]
            if current_type.lower() == 'uuid':
                print(f"   ✅ {table_name}.{column_name} is already UUID type, skipping...")
                continue
                
            print(f"   📝 Current type: {current_type}")
            
            # Step 2: Add temporary column for UUID conversion
            print("   🔧 Adding temporary UUID column...")
            db.execute(text(f"""
                ALTER TABLE {table_name} 
                ADD COLUMN temp_conversation_id UUID
            """))
            
            # Step 3: Convert valid UUID strings to UUID
            print("   🔄 Converting valid UUID strings to UUID...")
            db.execute(text(f"""
                UPDATE {table_name} 
                SET temp_conversation_id = {column_name}::UUID 
                WHERE {column_name} ~ '^[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}$'
            """))
            
            # Step 4: Drop the old column
            print("   🗑️ Dropping old column...")
            db.execute(text(f"""
                ALTER TABLE {table_name} 
                DROP COLUMN {column_name} CASCADE
            """))
            
            # Step 5: Rename temp column to original name
            print("   ✏️ Renaming temp column...")
            db.execute(text(f"""
                ALTER TABLE {table_name} 
                RENAME COLUMN temp_conversation_id TO {column_name}
            """))
            
            db.commit()
            print(f"   ✅ {table_name}.{column_name} successfully converted to UUID!")
            
        except Exception as e:
            print(f"   ❌ Error processing {table_name}: {e}")
            db.rollback()
            
    print("\n✅ Migration complete!")

if __name__ == "__main__":
    try:
        migrate_conversation_ids()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
    finally:
        db.close()
