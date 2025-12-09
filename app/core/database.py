import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Get the connection URL from the environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

# --- Create the Engine with the Fixed IPv4 Host ---
engine = create_engine(
    DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")  
)

# Create a configured "Session" class
# This class is used to create sessions for interacting with the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get a DB session (used by message handlers)
def get_db_session():
    """Provides a transactional scope around a series of operations."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
