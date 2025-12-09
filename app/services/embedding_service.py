import os
import logging
from typing import List, Dict, Any, Union

# --- CORE DEPENDENCIES ---

from openai import OpenAI 
from openai import APIError
from sqlalchemy.orm import Session 

# Assuming  message model is defined here:
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
            print(f"OpenAI Embedding client initialized with model: {EMBEDDING_MODEL}")
        except Exception as e:
            # Catch initialization failures (e.g., if the library is not installed)
            raise AppError(f"CRITICAL: Failed to initialize OpenAI client: {e}")

    # MANDATE 4.1: Type Safety
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
            # Extract the vector list from each data object in the response
            # The API call naturally handles the batching!
            return [data.embedding for data in response.data]
            
        except APIError as e:
            # Catch specific API errors (e.g., bad key, rate limit)
            raise AppError(f"OpenAI API Error during embedding.", 
                           context={"texts_count": len(texts), "error": str(e), "status_code": e.status_code})
        except Exception as e:
            # Catch general runtime errors
            raise AppError(f"General Embedding failed.", context={"error": str(e)})

# MANDATE 5.1: Dependency Injection Pattern
def get_embedding_service() -> EmbeddingService:
    """Dependency function to provide the stateless EmbeddingService instance."""
    if not hasattr(get_embedding_service, 'instance'):
        get_embedding_service.instance = EmbeddingService()
    return get_embedding_service.instance
    
# --- New Service Function for Ingestion (using the above class) ---

async def process_and_store_message(
    db: Session, 
    content: str, 
    user_id: int, 
    guild_id: int
):
    """
    Generates an embedding for a single message and saves it to the database.
    """
    embedding_service = get_embedding_service()
    
    # 1. Generate the Vector Embedding (We pass a single item list for the batch function)
    if not content or not content.strip():
        print("Skipping message due to empty content.")
        return

    try:
        # We call embed_batch but only give it one text, expecting one embedding back
        embedding_vector = embedding_service.embed_batch([content])[0]

    except AppError as e:
        print(f"Ingestion failed for message: {e}")
        return

    # 2. Create the Database Record
    new_message = DiscordMessage(
        user_id=str(user_id),
        guild_id=str(guild_id),
        content=content,
        vector=embedding_vector 
    )

    # 3. Commit to Database
    try:
        db.add(new_message)
        db.commit()
        # No need for refresh here, just logging the success
    except Exception as e:
        db.rollback()
        print(f"Database error during message save: {e}")
