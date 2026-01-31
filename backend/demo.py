"""
Demo script for Session Memory and Query Understanding Pipeline.

This script demonstrates:
1. Flow 1: Session Memory Trigger - Load long conversation, show summarization
2. Flow 2: Ambiguous Query Handling - Query rewriting and clarifying questions

Usage:
    cd backend
    python demo.py
"""

import asyncio
import json
from pathlib import Path

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.services.memory_service import memory_service
from src.services.query_service import query_service
from src.schemas.chat import Message, SessionMemory
from src.config import settings


def print_separator(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


async def demo_flow1_session_memory():
    """
    Flow 1: Demonstrate session memory trigger.
    - Load a long conversation
    - Show token count increasing
    - Trigger summarization
    - Print the generated summary
    """
    print_separator("FLOW 1: SESSION MEMORY TRIGGER")
    
    # Load test conversation
    test_file = Path(__file__).parent / "data" / "test_conversations" / "01_long_conversation_memory_trigger.json"
    
    with open(test_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create a new session
    session_id = "demo-session-memory"
    memory = SessionMemory(session_id=session_id)
    
    print(f"Session ID: {session_id}")
    print(f"Token threshold: {settings.TOKEN_THRESHOLD}")
    print(f"\nLoading conversation with {len(data['messages'])} messages...")
    print("-" * 40)
    
    # Add messages one by one and track token count
    for i, msg_data in enumerate(data['messages']):
        message = Message(role=msg_data['role'], content=msg_data['content'])
        memory = memory_service.add_message(memory, message)
        
        # Print progress every 5 messages
        if (i + 1) % 5 == 0 or i == len(data['messages']) - 1:
            print(f"Messages: {i + 1}/{len(data['messages'])} | Tokens: {memory.total_tokens}")
        
        # Check if summarization should be triggered
        if memory_service.should_summarize(memory):
            print(f"\n⚡ TOKEN THRESHOLD EXCEEDED! ({memory.total_tokens} > {settings.TOKEN_THRESHOLD})")
            print("Triggering summarization...")
            
            memory = await memory_service.summarize_session(memory)
            
            print("\n📋 GENERATED SUMMARY:")
            print("-" * 40)
            if memory.summary:
                summary_dict = memory.summary.model_dump()
                print(json.dumps(summary_dict, indent=2, ensure_ascii=False))
            
            print(f"\nMessage range summarized: {memory.message_range_summarized}")
            print(f"Remaining messages: {len(memory.messages)}")
            print(f"New token count: {memory.total_tokens}")
            break
    
    # Save memory to file
    memory_service.save_memory(memory)
    print(f"\n✅ Memory saved to: {settings.MEMORY_DIR / f'{session_id}.json'}")
    
    return memory


async def demo_flow2_ambiguous_queries(memory: SessionMemory = None):
    """
    Flow 2: Demonstrate ambiguous query handling.
    - Process ambiguous queries
    - Show query rewriting
    - Show context augmentation
    - Show clarifying questions
    """
    print_separator("FLOW 2: AMBIGUOUS QUERY HANDLING")
    
    # Load test data
    test_file = Path(__file__).parent / "data" / "test_conversations" / "02_ambiguous_queries.json"
    
    with open(test_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Use existing memory or create new
    if memory is None:
        memory = SessionMemory(session_id="demo-ambiguous")
    
    # Test with ambiguous queries from test data
    test_queries = [
        "Something nice for tonight",
        "She likes the one we went to last time",
        "What about it?"
    ]
    
    for query in test_queries:
        print(f"\n🔍 QUERY: \"{query}\"")
        print("-" * 40)
        
        result = await query_service.understand_query(query, memory)
        
        print(f"Is Ambiguous: {result.is_ambiguous}")
        
        if result.rewritten_query:
            print(f"Rewritten Query: {result.rewritten_query}")
        
        if result.needed_context_from_memory:
            print(f"Needed from memory: {result.needed_context_from_memory}")
        
        if result.clarifying_questions:
            print("Clarifying Questions:")
            for i, q in enumerate(result.clarifying_questions, 1):
                print(f"  {i}. {q}")
        
        print(f"\nFinal Augmented Context (truncated):")
        print(result.final_augmented_context[:300] + "..." if len(result.final_augmented_context) > 300 else result.final_augmented_context)
        
        print()


async def demo_full_pipeline():
    """
    Demonstrate the complete pipeline with a new query.
    """
    print_separator("FULL PIPELINE DEMO")
    
    # Create session with some context
    session_id = "demo-full-pipeline"
    memory = SessionMemory(session_id=session_id)
    
    # Add some context messages
    context_messages = [
        Message(role="user", content="I'm looking for a laptop for programming."),
        Message(role="assistant", content="I can help you find a good programming laptop! What's your budget and do you have any preferences for operating system?"),
        Message(role="user", content="Around $1500, and I prefer Linux."),
        Message(role="assistant", content="Great choices! For Linux development around $1500, I'd recommend looking at ThinkPad X1 Carbon or Dell XPS 15. Both have excellent Linux support."),
    ]
    
    for msg in context_messages:
        memory = memory_service.add_message(memory, msg)
    
    print(f"Session ID: {session_id}")
    print(f"Context messages: {len(memory.messages)}")
    print(f"Token count: {memory.total_tokens}")
    
    # Process an ambiguous follow-up query
    query = "What about the battery?"
    print(f"\n🔍 New Query: \"{query}\"")
    print("-" * 40)
    
    result = await query_service.understand_query(query, memory)
    
    print("\n📊 Query Understanding Result:")
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))


async def main():
    print("\n" + "=" * 60)
    print("  CHAT ASSISTANT DEMO")
    print("  Session Memory + Query Understanding Pipeline")
    print("=" * 60)
    
    # Flow 1: Session Memory
    memory = await demo_flow1_session_memory()
    
    # Flow 2: Ambiguous Queries
    await demo_flow2_ambiguous_queries(memory)
    
    # Full Pipeline
    await demo_full_pipeline()
    
    print_separator("DEMO COMPLETE")
    print("Check the backend/data/memory folder for saved session files.")


if __name__ == "__main__":
    asyncio.run(main())
