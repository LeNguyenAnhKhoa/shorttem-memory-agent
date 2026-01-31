from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


# ============== Request/Response Schemas ==============

class Message(BaseModel):
    """Single conversation message."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """Chat API request."""
    query: str
    session_id: str
    messages: Optional[List[Message]] = []


class ChatResponse(BaseModel):
    """Chat API response."""
    answer: str
    session_id: str


# ============== Session Summary Schema ==============

class UserProfile(BaseModel):
    """User preferences and constraints extracted from conversation."""
    preferences: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)


class SessionSummary(BaseModel):
    """
    Structured session summary schema.
    Generated when conversation exceeds token threshold.
    """
    user_profile: UserProfile = Field(default_factory=UserProfile)
    key_facts: List[str] = Field(default_factory=list, description="Important facts discussed")
    decisions: List[str] = Field(default_factory=list, description="Decisions made during conversation")
    open_questions: List[str] = Field(default_factory=list, description="Unresolved questions")
    todos: List[str] = Field(default_factory=list, description="Action items mentioned")


class SessionMemory(BaseModel):
    """Complete session memory stored on disk."""
    session_id: str
    summary: Optional[SessionSummary] = None
    message_range_summarized: Optional[dict] = None  # {"from": 0, "to": 42}
    messages: List[Message] = Field(default_factory=list)
    total_tokens: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ============== Query Understanding Schema ==============

class QueryUnderstanding(BaseModel):
    """
    Structured output from query understanding pipeline.
    """
    original_query: str
    is_ambiguous: bool = False
    rewritten_query: Optional[str] = None
    needed_context_from_memory: List[str] = Field(default_factory=list)
    clarifying_questions: List[str] = Field(default_factory=list)
    final_augmented_context: str = ""

