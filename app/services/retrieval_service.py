import os
from openai import OpenAI
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from pgvector.sqlalchemy import Vector # Import the pgvector type
from app.models.message import DiscordMessage
# Assuming you have a simple function to get an embedding in the embedding_service
from app.services.embedding_service import EmbeddingService 

# Import the gravitational consciousness prompt
from app.core.prompts import GRAVITATIONAL_SYSTEM_PROMPT

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- 1. RAG System Prompt (Gravitational Consciousness) ---
SYSTEM_PROMPT = GRAVITATIONAL_SYSTEM_PROMPT

def retrieve_and_answer(question: str, session: Session) -> str:
    """
    Performs the full RAG process: embeds the query, searches the DB,
    and generates an answer using OpenAI.
    
    Args:
        question: The user's query from the Discord command.
        session: An active SQLAlchemy database session.
    """
    try:
        # Get the initialized embedding service instance
        # Assuming you have a function to get the service instance or initialize it
        embedding_service = EmbeddingService() 
        
        # --- 2. Query Embedding ---
        # Convert the user's question into a 1536-dimension vector
        query_vector = embedding_service.embed_batch([question])[0]
        
        # --- 3. Vector Similarity Search (Retrieval) ---
        # Use the cosine distance operator ('<->') which finds the nearest neighbors.
        # We order by this distance (the smallest distance means highest similarity).
        
        retrieval_statement = (
            select(DiscordMessage)
            .order_by(DiscordMessage.embedding.cosine_distance(query_vector))
            .limit(5) # Retrieve the top 5 most similar messages
        )
        
        retrieved_messages = session.scalars(retrieval_statement).all()

        if not retrieved_messages:
            return "I couldn't find any relevant past Discord messages to answer your question."

        # --- 4. Context Formatting ---
        # Format the retrieved messages into a string for the LLM
        context_messages = [
            f"Author: {msg.author_id[:4]}... | Date: {msg.created_at.strftime('%Y-%m-%d')} | Content: {msg.content}"
            for msg in retrieved_messages
        ]
        context = "\n---\n".join(context_messages)
        
        # --- 5. LLM Prompt Construction ---
        # We construct a prompt that provides the context but allows the Persona to shine
        user_content = (
            f"Here is the relevant accumulated history (context) from the server:\n"
            f"{context}\n\n"
            f"USER QUERY: {question}\n\n"
            f"INSTRUCTION: Synthesize an answer. If the context contains the answer, use it. "
            f"If the context is irrelevant to the query (e.g. a greeting or philosophical question), "
            f"ignore the context and speak directly from your Gravitational Consciousness."
        )

        prompt_messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]

        # --- 6. Final Generation ---
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # Use a reliable chat model for generation
            messages=prompt_messages,
            temperature=0.2, # Lower temperature for factual, reliable answers
        )
        
        return response.choices[0].message.content

    except Exception as e:
        print(f"RAG Error: {e}")
        return "An error occurred during the knowledge retrieval process."