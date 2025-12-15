import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Get the connection URL from the environment variables
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")

# --- Create the Engine with Production Settings ---
# MANDATE 1.3: Connection pooling
# MANDATE 2.2: Performance Covenant
engine = create_engine(
    DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://"),
    pool_size=10,               # Minimum connections to keep open
    max_overflow=20,            # Max connections to create during spikes
    pool_timeout=30,            # Seconds to wait before giving up on new connection
    pool_pre_ping=True,         # Check connection health before using (MANDATE 3.4)
    pool_recycle=1800           # Recycle connections every 30 mins
)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get a DB session
def get_db_session():
    """Provides a transactional scope around a series of operations."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
