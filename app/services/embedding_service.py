import numpy as np
import logging
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Union

# MANDATE 2.1: Structured Error Hierarchy 
# Define a base error for your application
class AppError(Exception):
    """Base application error with logging context"""
    def __init__(self, message: str, context: Dict[str, Any] = None):
        self.context = context or {}
        # NOTE: In a production system, this would call a structured logger (2.3)
        print(f"AppError: {message} Context: {self.context}") 
        super().__init__(message)

# MANDATE 4.2: Single Responsibility Law
class EmbeddingService:
    def __init__(self):
        """
        Initializes the model. This happens only once when the bot starts.
        We choose a model optimized for speed and quality (384 dimensions).
        """
        try:
            # We assume this model is installed via requirements.txt
            self.model = SentenceTransformer('all-MiniLM-L6-v2') 
            print("Embedding model loaded successfully.")
        except Exception as e:
            # MANDATE 2.1: Catch and handle critical initialization failure
            raise AppError(f"CRITICAL: Failed to load Sentence Transformer model: {e}")

    # MANDATE 4.1: Type Safety - Explicit return type Mapped[List[float]]
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Converts a list of texts into a list of embedding vectors.
        """
        if not texts:
            return []
            
        try:
            # Encode method converts the text list into a NumPy array of vectors
            embeddings = self.model.encode(texts, convert_to_numpy=True)
            # We convert the NumPy array to a standard list of floats for storage in PostgreSQL
            return embeddings.tolist()
        except Exception as e:
            # MANDATE 2.1: Structured Error Handling for runtime failure
            raise AppError(f"Embedding failed during encoding.", context={"texts_count": len(texts), "error": str(e)})
            
# MANDATE 5.1: Dependency Injection Pattern
# Provides a single, reusable instance of the expensive-to-load model.
def get_embedding_service() -> EmbeddingService:
    """Dependency function to provide the stateless EmbeddingService instance."""
    # We load the service here, once per application process.
    if not hasattr(get_embedding_service, 'instance'):
        get_embedding_service.instance = EmbeddingService()
    return get_embedding_service.instance
