import numpy as np
from datetime import datetime
from typing import List

# Import necessary SQLAlchemy 2.0 components
from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Import the Vector type from the pgvector library
# This is crucial for MANDATE 5.3
from pgvector.sqlalchemy import Vector 

# --- BASE DECLARATION (The Foundation) ---
# Every model must inherit from this
class Base(DeclarativeBase):
    """Base class which provides automated table name
    and default timestamp columns."""
    pass

# --- DISCORD MESSAGE MODEL (The Data Structure) ---
class DiscordMessage(Base):
    """
    Represents a single message from Discord, including its semantic embedding.
    """
    __tablename__ = "discord_messages"  # MANDATORY Table Name (1.3)
    
    # Primary Key - Unique ID
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # Discord Metadata
    # We use BIGINT for Discord IDs as they are too large for standard INT
    discord_id: Mapped[str] = mapped_column(String(50), index=True, unique=True)
    channel_id: Mapped[str] = mapped_column(String(50), index=True)
    author_id: Mapped[str] = mapped_column(String(50), index=True)
    
    # Message Content
    content: Mapped[str] = mapped_column(String)
    
    # --- The Core Vector Column (MANDATE 5.3) ---
    # We anticipate using a popular model (like BAAI/bge-small-en-v1.5) 
    # which has 384 dimensions. This must match your chosen model's output size.
    # The Mapped[List[float]] provides Python type hinting for the vector array.
    embedding: Mapped[List[float]] = mapped_column(Vector(1536))
    
    # Timestamps (MANDATE 4.1: Data Integrity)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        index=True
    )
    
    def __repr__(self) -> str:
        return (f"DiscordMessage(id={self.id!r}, "
                f"content='{self.content[:30]}...', "
                f"vector_dims={len(self.embedding)})")
