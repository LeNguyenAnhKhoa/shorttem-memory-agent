"""
Agent Service - Main chat pipeline.

Pipeline:
1. Chat input → Load session memory
2. Check token threshold → Trigger summarization if needed  
3. Query understanding → Rewrite, augment context, clarifying questions
4. Final prompt construction → Generate response
5. Save updated memory
"""

import json
import logging
from typing import List, Dict, AsyncGenerator
from datetime import datetime

from openai import OpenAI

from src.config import settings
from src.schemas.chat import Message, SessionMemory, QueryUnderstanding
from src.services.memory_service import memory_service
from src.services.query_service import query_service

logger = logging.getLogger(__name__)


class AgentService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def process_query(
        self,
        query: str,
        session_id: str,
        messages: List[Message] = None
    ) -> AsyncGenerator[str, None]:
        """
        Main chat processing pipeline.
        
        Yields streaming JSON chunks with types:
        - pipeline_step: Current step in pipeline
        - summary: Session summary (when triggered)
        - query_understanding: Query analysis result
        - clarifying_questions: Questions for user (if any)
        - answer: Final response
        """
        try:
            # Step 1: Load session memory
            yield json.dumps({
                "type": "pipeline_step",
                "content": "Loading session memory..."
            }) + "\n"
            
            memory = memory_service.load_memory(session_id)
            
            # Add incoming messages to memory if provided
            if messages:
                for msg in messages:
                    if msg not in memory.messages:
                        memory = memory_service.add_message(memory, msg)
            
            # Add current query as user message
            user_message = Message(
                role="user",
                content=query,
                timestamp=datetime.now()
            )
            memory = memory_service.add_message(memory, user_message)
            
            # Step 2: Check if summarization needed
            yield json.dumps({
                "type": "pipeline_step",
                "content": f"Token count: {memory.total_tokens}/{settings.TOKEN_THRESHOLD}"
            }) + "\n"
            
            if memory_service.should_summarize(memory):
                yield json.dumps({
                    "type": "pipeline_step",
                    "content": "Token threshold exceeded, triggering summarization..."
                }) + "\n"
                
                memory = await memory_service.summarize_session(memory)
                
                # Send summary to frontend
                if memory.summary:
                    yield json.dumps({
                        "type": "summary",
                        "content": memory.summary.model_dump()
                    }) + "\n"
            
            # Step 3: Query understanding
            yield json.dumps({
                "type": "pipeline_step",
                "content": "Analyzing query..."
            }) + "\n"
            
            query_result = await query_service.understand_query(query, memory)
            
            yield json.dumps({
                "type": "query_understanding",
                "content": query_result.model_dump()
            }) + "\n"
            
            # Step 4: Check for clarifying questions
            if query_result.clarifying_questions:
                yield json.dumps({
                    "type": "clarifying_questions",
                    "content": query_result.clarifying_questions
                }) + "\n"
            
            # Step 5: Generate response
            yield json.dumps({
                "type": "pipeline_step",
                "content": "Generating response..."
            }) + "\n"
            
            response = await self._generate_response(query_result)
            
            # Add assistant response to memory
            assistant_message = Message(
                role="assistant",
                content=response,
                timestamp=datetime.now()
            )
            memory = memory_service.add_message(memory, assistant_message)
            
            # Save memory
            memory_service.save_memory(memory)
            
            # Send final answer
            yield json.dumps({
                "type": "answer",
                "content": response
            }) + "\n"
            
        except Exception as e:
            logger.error(f"Error in pipeline: {e}", exc_info=True)
            yield json.dumps({
                "type": "answer",
                "content": f"Sorry, an error occurred: {str(e)}"
            }) + "\n"
    
    async def _generate_response(self, query_result: QueryUnderstanding) -> str:
        """Generate final response using augmented context."""
        
        system_prompt = """You are a helpful chat assistant. Use the provided context to answer the user's question.
If the query was rewritten for clarity, use the rewritten version.
Be concise and helpful."""

        try:
            response = self.client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query_result.final_augmented_context}
                ],
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return settings.ERROR_MESSAGE


# Singleton instance
agent_service = AgentService()
