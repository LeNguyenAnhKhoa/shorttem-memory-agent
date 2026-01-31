# Chat Assistant with Session Memory

A simple chat assistant demonstrating:
1. **Session Memory via Summarization** - Automatic summarization when conversation context exceeds a configurable token threshold
2. **Query Understanding Pipeline** - Rewriting ambiguous queries, context augmentation, and clarifying questions

## Architecture

```
User Query → Load Session Memory → Check Token Threshold → Query Understanding → Generate Response
                    ↓                      ↓                      ↓
              Load/Create            Summarize if             - Detect ambiguity
              from disk              exceeded                 - Rewrite query
                                                             - Augment context
                                                             - Generate clarifying Qs
```

## Features

### A. Session Memory via Summarization
- **Trigger**: When conversation context exceeds configurable threshold (default: 10k tokens)
- **Token Counting**: Uses `tiktoken` with `o200k_base` model
- **Output Schema**:
```json
{
  "session_summary": {
    "user_profile": {"preferences": [], "constraints": []},
    "key_facts": [],
    "decisions": [],
    "open_questions": [],
    "todos": []
  },
  "message_range_summarized": {"from": 0, "to": 42}
}
```

### B. Query Understanding Pipeline
1. **Rewrite/Paraphrase**: Detect and rewrite ambiguous queries
2. **Context Augmentation**: Combine recent messages + session memory
3. **Clarifying Questions**: Generate 1-3 questions if intent unclear

**Output Schema**:
```json
{
  "original_query": "...",
  "is_ambiguous": true,
  "rewritten_query": "...",
  "needed_context_from_memory": ["user_profile.preferences"],
  "clarifying_questions": ["...", "..."],
  "final_augmented_context": "..."
}
```

## Project Structure

```
backend/
├── app.py                      # FastAPI application
├── demo.py                     # Demo script for both flows
├── data/
│   ├── memory/                 # Session memory storage (JSON files)
│   └── test_conversations/     # Test data (3 conversation logs)
└── src/
    ├── config.py               # Configuration (token threshold, etc.)
    ├── schemas/
    │   └── chat.py             # Pydantic schemas (SessionSummary, QueryUnderstanding)
    ├── services/
    │   ├── agent_service.py    # Main chat pipeline
    │   ├── memory_service.py   # Session memory with summarization
    │   └── query_service.py    # Query understanding pipeline
    └── routers/
        └── agent.py            # API endpoints

frontend/
└── src/app/page.tsx            # React chat interface
```

## Setup

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Create .env file with your OpenAI API key
echo OPENAI_API_KEY=your_key_here > .env

# Run server
uvicorn app:app --reload --port 8000
```

### Frontend
```bash
cd frontend
pnpm install

# Create .env.local
echo NEXT_PUBLIC_BACKEND_URL=http://localhost:8000 > .env.local

pnpm dev
```

## Demo

Run the demo script to see both flows:

```bash
cd backend
python demo.py
```

This demonstrates:
1. **Flow 1**: Loading a long conversation → Token threshold exceeded → Summarization triggered
2. **Flow 2**: Ambiguous queries → Rewriting → Context augmentation → Clarifying questions

## Test Data

Three conversation logs in `backend/data/test_conversations/`:

1. **01_long_conversation_memory_trigger.json** - Long conversation that triggers summarization
2. **02_ambiguous_queries.json** - Examples of ambiguous user queries
3. **03_context_building.json** - Shows how context builds over conversation

## API Endpoints

- `POST /api/v0/chat/` - Main chat endpoint (streaming response)
- `GET /api/v0/chat/session/{session_id}` - Get session memory
- `DELETE /api/v0/chat/session/{session_id}` - Clear session memory
- `GET /api/v0/health/` - Health check

## Configuration

Edit `backend/src/config.py`:

```python
TOKEN_THRESHOLD: int = 10000      # Trigger summarization threshold
TIKTOKEN_MODEL: str = "o200k_base" # Token counting model
RECENT_MESSAGES_COUNT: int = 5    # Messages to keep after summarization
```

## License

MIT
