from pydantic import BaseModel, Field, validator
from typing import Optional

# MANDATE 5.4: Pydantic Base Model for Type Checking and Validation
class MessageIngestSchema(BaseModel):
    """
    Pydantic validation schema for data received from the Discord bot listener.
    """
    # Discord IDs are too large for standard Python int, so we treat them as strings
    discord_id: str = Field(..., description="Unique Discord ID of the message.")
    author_id: str = Field(..., description="Discord ID of the author.")
    channel_id: str = Field(..., description="Discord ID of the channel.")
    
    # Message content length constraint is vital for performance (MANDATE 2.2)
    content: str = Field(..., min_length=1, max_length=5000, 
                         description="The actual text content of the message.")
    
    # MANDATE 1.4: Input validation function (5.4)
    # Checks for basic security issues or overly long text before processing.
    @validator('content')
    def check_content_safety(cls, v):
        # Prevent huge messages from crashing the embedding service 
        if len(v) > 4000:
            raise ValueError("Content exceeds processing limit (4000 characters).")
        # Basic check against potential injection (can be expanded)
        if "DROP TABLE" in v.upper():
            raise ValueError("Potential malicious input detected.")
        return v
