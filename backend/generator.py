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

# Configure logging to suppress extensive output if needed, or keep strictly print based
logging.basicConfig(level=logging.ERROR)

async def main():
    # Path to the conversation file
    conversation_file = os.path.join(current_dir, 'data', 'test_conversations', '01_long_conversation_memory_trigger.json')
    
    if not os.path.exists(conversation_file):
        print(f"Error: File not found at {conversation_file}")
        return

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

    # Generate a unique session ID for this run
    session_id = f"gen_test_{uuid.uuid4().hex[:8]}"
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
                    # We can optionally parse the chunk here if we want to print progress
                    # chunk_data = json.loads(response_chunk)
                    # if chunk_data.get("type") == "answer":
                    #     print(f"Assistant: {chunk_data.get('content')}")
                    pass
                
                print("-> processed successfully.")
                user_messages_count += 1
                
            except Exception as e:
                print(f"Error processing message: {e}")

    print("-" * 50)
    print(f"Simulation complete.")
    print(f"Processed {user_messages_count} user messages.")
    print(f"Memory file should be available at: backend/data/memory/{session_id}.json")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
