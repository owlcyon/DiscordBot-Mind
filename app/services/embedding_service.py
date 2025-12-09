import os
import logging
from typing import List, Dict, Any

# --- CORE DEPENDENCIES ---
from openai import OpenAI 
from openai import APIError
from sqlalchemy.orm import Session 

# Import message model
from app.models.message import DiscordMessage 

# --- CONFIGURATION ---
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536 # The size of the vector from this model

# MANDATE 2.1: Structured Error Hierarchy 
class AppError(Exception):
    """Base application error with logging context"""
    def __init__(self, message: str, context: Dict[str, Any] = None):
        self.context = context or {}
        print(f"AppError: {message} Context: {self.context}") 
        super().__init__(message)

# MANDATE 4.2: Single Responsibility Law
class EmbeddingService:
    def __init__(self):
        """
        Initializes the OpenAI client. This happens once when the bot starts.
        The client automatically finds the OPENAI_API_KEY from the environment.
        """
        try:
            self.client = OpenAI()
            print(f"✅ OpenAI Embedding client initialized with model: {EMBEDDING_MODEL}")
        except Exception as e:
            raise AppError(f"CRITICAL: Failed to initialize OpenAI client: {e}")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Converts a list of texts into a list of embedding vectors using the OpenAI API.
        """
        if not texts:
            return []
            
        try:
            response = self.client.embeddings.create(
                input=texts,
                model=EMBEDDING_MODEL
            )
            return [data.embedding for data in response.data]
            
        except APIError as e:
            raise AppError(
                f"OpenAI API Error during embedding.", 
                context={
                    "texts_count": len(texts), 
                    "error": str(e), 
                    "status_code": getattr(e, 'status_code', 'unknown')
                }
            )
        except Exception as e:
            raise AppError(f"General Embedding failed.", context={"error": str(e)})

# MANDATE 5.1: Dependency Injection Pattern
def get_embedding_service() -> EmbeddingService:
    """Dependency function to provide the stateless EmbeddingService instance."""
    if not hasattr(get_embedding_service, 'instance'):
        get_embedding_service.instance = EmbeddingService()
    return get_embedding_service.instance
    
# --- Service Function for Message Ingestion ---

async def process_and_store_message(
    db: Session, 
    discord_message_id: str,
    author_id: str,
    channel_id: str,
    content: str
):
    """
    Generates an embedding for a single message and saves it to the database.
    
    Args:
        db: SQLAlchemy database session
        discord_message_id: The unique Discord message ID
        author_id: Discord user ID of the message author
        channel_id: Discord channel ID where message was sent
        content: The message text content
    """
    # Validate input
    if not content or not content.strip():
        print("⚠️  Skipping message due to empty content.")
        return

    # Check for content length
    if len(content) > 4000:
        print(f"⚠️  Skipping message due to excessive length: {len(content)} characters")
        return

    embedding_service = get_embedding_service()

    try:
        # 1. Generate the Vector Embedding
        embedding_vector = embedding_service.embed_batch([content])[0]

        # 2. Create the Database Record (matching your model fields)
        new_message = DiscordMessage(
            discord_id=discord_message_id,
            author_id=author_id,
            channel_id=channel_id,
            content=content,
            embedding=embedding_vector  # This matches your model's field name
        )

        # 3. Commit to Database
        db.add(new_message)
        db.commit()
        print(f"✅ Message {discord_message_id} embedded and stored successfully")

    except AppError as e:
        print(f"❌ Embedding generation failed: {e}")
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        print(f"❌ Database error during message save: {e}")
        raise