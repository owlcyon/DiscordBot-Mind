import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv 

# --- 1. Load Environment Variables ---
load_dotenv() 

# --- 2. Get DB URL and Dependencies ---
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("CRITICAL: DATABASE_URL not found in .env. Cannot proceed.")
    sys.exit(1)

from app.models.message import Base 

# --- 3. Define the Database Engine ---
engine = create_engine(
    DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")
)

# --- 4. Step 1: Ensure the vector extension is active (MANDATE 1.3) ---
try:
    with engine.begin() as connection:
        print("Attempting to create 'vector' extension if it doesn't exist...")
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        connection.commit()
        print("Vector extension check complete.")
except Exception as e:
    print(f"CRITICAL: Failed to connect or create extension. Error: {e}")
    sys.exit(1)

# --- 5. Step 2: Create all tables defined in Base ---
print(f"Creating tables defined in Base.metadata for engine: {engine.url.host}")
Base.metadata.create_all(bind=engine)
print("✅ Database tables created successfully (or already exist).")