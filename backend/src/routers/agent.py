from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.schemas.chat import ChatRequest, Message
from src.services.agent_service import agent_service
from src.services.memory_service import memory_service
from src.config import settings

router = APIRouter(
    prefix=f"/api/{settings.API_VERSION}/chat",
    tags=["Chat"]
)


@router.post("/")
async def chat(request: ChatRequest):
    """
    Chat endpoint with session memory and query understanding.
    
    Pipeline:
    1. Load session memory
    2. Check token threshold → Summarize if needed
    3. Query understanding → Rewrite, augment, clarify
    4. Generate response
    5. Save updated memory
    
    Returns streaming response with pipeline steps.
    """
    try:
        return StreamingResponse(
            agent_service.process_query(
                query=request.query,
                session_id=request.session_id,
                messages=request.messages
            ),
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """
    Get session memory for a given session ID.
    Useful for debugging and demo purposes.
    """
    try:
        memory = memory_service.load_memory(session_id)
        return memory.model_dump(mode='json')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """
    Clear session memory for a given session ID.
    """
    try:
        path = memory_service._get_memory_path(session_id)
        if path.exists():
            path.unlink()
        return {"message": f"Session {session_id} cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
