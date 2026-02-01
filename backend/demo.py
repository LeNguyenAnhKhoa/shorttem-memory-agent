import asyncio
import json
import os
import sys
import uuid
import logging

# Add the current directory to sys.path to allow imports from src
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.services.agent_service import agent_service
from src.schemas.chat import Message
from src.config import settings

# Configure logging to suppress extensive output if needed, or keep strictly print based
logging.basicConfig(level=logging.ERROR)

async def run_test_case(file_name):
    conversation_file = os.path.join(current_dir, 'data', 'test_conversations', file_name)
    
    if not os.path.exists(conversation_file):
        print(f"Error: File not found at {conversation_file}")
        return

    print(f"\n{'='*20} Running Test Case: {file_name} {'='*20}")
    print(f"Reading conversation from: {conversation_file}")
    
    try:
        with open(conversation_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return

    messages = data.get('messages', [])
    if not messages:
        print("No messages found in the file.")
        return

    # Generate a unique session ID for this run, based on file name for clarity
    # Remove extension and append simplified uuid
    base_name = os.path.splitext(file_name)[0]
    session_id = f"{base_name}_{uuid.uuid4().hex[:4]}"
    
    print(f"Starting simulation for Session ID: {session_id}")
    print("-" * 50)

    user_messages_count = 0
    
    for i, msg in enumerate(messages):
        if msg.get('role') == 'user':
            content = msg.get('content', '')
            print(f"\nProcessing User Message [{i+1}]: {content}")
            
            try:
                # Iterate through the generator to execute the pipeline
                async for response_chunk in agent_service.process_query(
                    query=content,
                    session_id=session_id
                ):
                    chunk_data = json.loads(response_chunk)
                    if chunk_data.get("type") == "answer":
                       print(f"Assistant: {chunk_data.get('content')}")
                    elif chunk_data.get("type") == "query_understanding":
                        print(f"Query Understanding: {chunk_data.get('content')}") # Print understanding for ambiguous tests
                    elif chunk_data.get("type") == "summary":
                        print(f"*** MEMORY TRIGGERED & UPDATED ***")
                
                print("-> processed successfully.")
                user_messages_count += 1
                
            except Exception as e:
                print(f"Error processing message: {e}")

    print("-" * 50)
    print(f"Simulation complete for {file_name}.")
    print(f"Processed {user_messages_count} user messages.")
    print(f"Memory file should be available at: backend/data/memory/{session_id}.json")

async def main():
    # Lower threshold to ensure triggering in demo
    settings.TOKEN_THRESHOLD = 500 
    print(f"Test Configuration: TOKEN_THRESHOLD set to {settings.TOKEN_THRESHOLD}")

    test_files = [
        'case_1_memory_trigger.json',
        'case_2_ambiguous_query.json',
        'case_3_context_aware.json'
    ]

    for test_file in test_files:
        await run_test_case(test_file)


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
