"""
Memory Service - Handles session memory with automatic summarization.

Pipeline:
1. Load/create session memory
2. Count tokens using tiktoken
3. Trigger summarization when threshold exceeded
4. Store summary as short-term memory
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional

import tiktoken
from openai import OpenAI

from src.config import settings
from src.schemas.chat import Message, SessionMemory, SessionSummary, UserProfile

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.encoding = tiktoken.get_encoding(settings.TIKTOKEN_MODEL)
        
    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken."""
        return len(self.encoding.encode(text))
    
    def count_messages_tokens(self, messages: List[Message]) -> int:
        """Count total tokens in a list of messages."""
        total = 0
        for msg in messages:
            total += self.count_tokens(f"{msg.role}: {msg.content}")
        return total
    
    def _get_memory_path(self, session_id: str) -> Path:
        """Get file path for session memory."""
        return settings.MEMORY_DIR / f"{session_id}.json"
    
    def load_memory(self, session_id: str) -> SessionMemory:
        """Load session memory from disk or create new."""
        path = self._get_memory_path(session_id)
        
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return SessionMemory(**data)
            except Exception as e:
                logger.error(f"Error loading memory: {e}")
        
        return SessionMemory(session_id=session_id)
    
    def save_memory(self, memory: SessionMemory) -> None:
        """Save session memory to disk."""
        memory.updated_at = datetime.now()
        path = self._get_memory_path(memory.session_id)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(memory.model_dump(mode='json'), f, ensure_ascii=False, indent=2, default=str)
    
    def add_message(self, memory: SessionMemory, message: Message) -> SessionMemory:
        """Add a message to session memory."""
        memory.messages.append(message)
        memory.total_tokens = self.count_messages_tokens(memory.messages)
        return memory
    
    def should_summarize(self, memory: SessionMemory) -> bool:
        """Check if summarization should be triggered."""
        return memory.total_tokens > settings.TOKEN_THRESHOLD
    
    async def summarize_session(self, memory: SessionMemory) -> SessionMemory:
        """
        Summarize the conversation when token threshold is exceeded.
        
        Returns updated memory with summary and truncated messages.
        """
        if not memory.messages:
            return memory
        
        logger.info(f"Triggering summarization for session {memory.session_id}")
        logger.info(f"Current tokens: {memory.total_tokens}, Threshold: {settings.TOKEN_THRESHOLD}")
        
        # Prepare conversation for summarization
        conversation_text = "\n".join([
            f"{msg.role}: {msg.content}" for msg in memory.messages
        ])
        
        # Generate summary using structured output
        try:
            response = self.client.beta.chat.completions.parse(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a conversation summarizer. Analyze the conversation and extract:
1. User profile: preferences and constraints mentioned
2. Key facts: important information discussed
3. Decisions: any decisions made
4. Open questions: unresolved questions
5. Todos: action items mentioned

Be concise and focus on information that would be useful for future context."""
                    },
                    {
                        "role": "user",
                        "content": f"Summarize this conversation:\n\n{conversation_text}"
                    }
                ],
                response_format=SessionSummary
            )
            
            summary = response.choices[0].message.parsed
            
            # Update memory with summary
            memory.summary = summary
            memory.message_range_summarized = {
                "from": 0,
                "to": len(memory.messages) - 1
            }
            
            # Keep only recent messages after summarization
            keep_count = settings.RECENT_MESSAGES_COUNT
            memory.messages = memory.messages[-keep_count:] if len(memory.messages) > keep_count else memory.messages
            memory.total_tokens = self.count_messages_tokens(memory.messages)
            
            logger.info(f"Summarization complete. New token count: {memory.total_tokens}")
            
        except Exception as e:
            logger.error(f"Error during summarization: {e}")
        
        return memory
    
    def get_context_from_memory(self, memory: SessionMemory, fields: List[str]) -> str:
        """
        Get specific fields from session summary for context augmentation.
        
        Args:
            memory: Session memory
            fields: List of field names like ["user_profile.preferences", "key_facts"]
        """
        if not memory.summary:
            return ""
        
        context_parts = []
        summary_dict = memory.summary.model_dump()
        
        for field in fields:
            parts = field.split('.')
            value = summary_dict
            
            try:
                for part in parts:
                    value = value[part]
                
                if value:
                    if isinstance(value, list):
                        context_parts.append(f"{field}: {', '.join(str(v) for v in value)}")
                    else:
                        context_parts.append(f"{field}: {value}")
            except (KeyError, TypeError):
                continue
        
        return "\n".join(context_parts)
    
    def get_recent_messages(self, memory: SessionMemory, count: int = None) -> List[Message]:
        """Get recent messages for context."""
        count = count or settings.RECENT_MESSAGES_COUNT
        return memory.messages[-count:] if memory.messages else []


# Singleton instance
memory_service = MemoryService()
