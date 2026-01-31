"""
Query Understanding Service - Pipeline for query processing.

Pipeline:
1. Rewrite/Paraphrase: Detect ambiguity and rewrite if needed
2. Context Augmentation: Combine recent messages + session memory
3. Clarifying Questions: Generate questions if still unclear
"""

import logging
from typing import List, Optional

from openai import OpenAI

from src.config import settings
from src.schemas.chat import Message, SessionMemory, QueryUnderstanding
from src.services.memory_service import memory_service

logger = logging.getLogger(__name__)


class QueryService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def understand_query(
        self,
        query: str,
        memory: SessionMemory
    ) -> QueryUnderstanding:
        """
        Main query understanding pipeline.
        
        Steps:
        1. Detect ambiguity and rewrite if needed
        2. Determine needed context from memory
        3. Build augmented context
        4. Generate clarifying questions if still unclear
        """
        
        # Get recent messages for context
        recent_messages = memory_service.get_recent_messages(memory)
        recent_context = "\n".join([
            f"{msg.role}: {msg.content}" for msg in recent_messages
        ]) if recent_messages else "No recent messages."
        
        # Get summary context if available
        summary_context = ""
        if memory.summary:
            summary_context = f"""
Session Summary:
- User preferences: {', '.join(memory.summary.user_profile.preferences) or 'None'}
- Constraints: {', '.join(memory.summary.user_profile.constraints) or 'None'}
- Key facts: {', '.join(memory.summary.key_facts) or 'None'}
- Open questions: {', '.join(memory.summary.open_questions) or 'None'}
"""
        
        # Call LLM to analyze query
        try:
            response = self.client.beta.chat.completions.parse(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": """You are a query understanding assistant. Analyze the user's query and:

1. Determine if the query is ambiguous (missing context, unclear intent, vague references)
2. If ambiguous, rewrite it to be clearer based on available context
3. Identify which parts of session memory would help answer the query
4. If the query is still unclear after rewriting, generate 1-3 clarifying questions

Be concise. Focus on understanding user intent."""
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze this query:

Query: {query}

Recent conversation:
{recent_context}

{summary_context}

Provide your analysis as structured output."""
                    }
                ],
                response_format=QueryUnderstanding
            )
            
            result = response.choices[0].message.parsed
            result.original_query = query
            
            # Build final augmented context
            context_parts = []
            
            # Add recent messages
            if recent_messages:
                context_parts.append("Recent conversation:\n" + recent_context)
            
            # Add relevant memory fields
            if result.needed_context_from_memory and memory.summary:
                memory_context = memory_service.get_context_from_memory(
                    memory, result.needed_context_from_memory
                )
                if memory_context:
                    context_parts.append("From session memory:\n" + memory_context)
            
            # Add rewritten query or original
            effective_query = result.rewritten_query if result.is_ambiguous and result.rewritten_query else query
            context_parts.append(f"User query: {effective_query}")
            
            result.final_augmented_context = "\n\n".join(context_parts)
            
            logger.info(f"Query understanding complete. Ambiguous: {result.is_ambiguous}")
            return result
            
        except Exception as e:
            logger.error(f"Error in query understanding: {e}")
            # Return basic result on error
            return QueryUnderstanding(
                original_query=query,
                is_ambiguous=False,
                final_augmented_context=f"Recent conversation:\n{recent_context}\n\nUser query: {query}"
            )


# Singleton instance
query_service = QueryService()
