"""
Chat REST API routes.

Provides REST endpoints for chat interactions as a backup for clients
that cannot use WebSocket. For real-time streaming, use /ws/stream.

All routes require authentication - conversations are scoped to users.
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, List
import logging

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel

from app.models.requests import ChatMessage
from app.models.responses import (
    ChatAcceptedResponse,
    ChatResponse,
    ConversationHistory,
    HistoryMessage,
)
from app.models.database import User
from app.core.config import get_settings
from app.core.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory conversation storage keyed by user_id -> conversation_id -> messages
# Structure: {user_id: {conversation_id: [messages]}}
# Replace with database in production (Phase 6.2)
user_conversations: Dict[str, Dict[str, List[Dict]]] = {}
user_pending_tasks: Dict[str, Dict[str, Dict]] = {}


class ConversationCreate(BaseModel):
    """Request to create a new conversation."""
    title: Optional[str] = None


class ConversationInfo(BaseModel):
    """Basic conversation information."""
    conversation_id: str
    title: Optional[str]
    message_count: int
    created_at: datetime
    last_message_at: Optional[datetime]


@router.post("/", response_model=ChatAcceptedResponse)
async def send_message(
    chat_message: ChatMessage,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
):
    """
    Send a chat message for agent processing.
    
    This is a REST alternative to WebSocket streaming. The message is
    accepted immediately and processed in the background. Use the
    conversation endpoint to poll for results.
    
    For real-time streaming, use WebSocket at /ws/stream instead.
    
    Requires authentication - conversations are scoped to the authenticated user.
    """
    user_id = str(user.id)
    
    # Initialize user's conversation storage if new
    if user_id not in user_conversations:
        user_conversations[user_id] = {}
        user_pending_tasks[user_id] = {}
    
    # Generate or use existing conversation ID
    conversation_id = chat_message.conversation_id or str(uuid.uuid4())
    
    # Initialize conversation if new
    if conversation_id not in user_conversations[user_id]:
        user_conversations[user_id][conversation_id] = []
    
    # Store user message
    user_conversations[user_id][conversation_id].append({
        "role": "user",
        "content": chat_message.message,
        "timestamp": datetime.now().isoformat(),
    })
    
    # Mark task as pending
    user_pending_tasks[user_id][conversation_id] = {
        "status": "processing",
        "started_at": datetime.now().isoformat(),
    }
    
    # Process in background
    background_tasks.add_task(
        process_chat_message,
        user_id,
        conversation_id,
        chat_message.message,
    )
    
    return ChatAcceptedResponse(
        conversation_id=conversation_id,
        status="accepted",
        message="Message accepted for processing. Poll /chat/{conversation_id} for results.",
    )


async def process_chat_message(user_id: str, conversation_id: str, message: str):
    """
    Process a chat message using the agent service.
    
    This runs in the background after the REST endpoint returns.
    """
    try:
        from app.services.agent_service import AgentService
        
        agent_service = AgentService(user_id=user_id)
        agents_used = []
        final_content = ""
        charts_generated = []
        
        # Collect all events from the streaming response
        async for event in agent_service.run_streaming(message):
            event_type = event.type if hasattr(event, 'type') else getattr(event, '__class__', '').__name__
            
            if event_type == "agent_step":
                if event.agent not in agents_used:
                    agents_used.append(event.agent)
            elif event_type == "chart":
                charts_generated.append(event.url)
            elif event_type == "result":
                final_content = event.content
        
        # Store assistant response
        user_conversations[user_id][conversation_id].append({
            "role": "assistant",
            "content": final_content,
            "agents_used": agents_used,
            "charts_generated": charts_generated,
            "timestamp": datetime.now().isoformat(),
        })
        
        # Mark task as complete
        user_pending_tasks[user_id][conversation_id] = {
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.exception(f"Error processing message for {conversation_id}")
        
        # Store error response
        user_conversations[user_id][conversation_id].append({
            "role": "error",
            "content": f"Processing failed: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        })
        
        user_pending_tasks[user_id][conversation_id] = {
            "status": "error",
            "error": str(e),
            "completed_at": datetime.now().isoformat(),
        }


@router.get("/{conversation_id}", response_model=ConversationHistory)
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
):
    """
    Get conversation history and current status.
    
    Poll this endpoint after sending a message to get the result.
    Only returns conversations owned by the authenticated user.
    """
    user_id = str(user.id)
    
    if user_id not in user_conversations or conversation_id not in user_conversations[user_id]:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = []
    for msg in user_conversations[user_id][conversation_id]:
        messages.append(HistoryMessage(
            role=msg["role"],
            content=msg["content"],
            agent_name=msg.get("agent_name"),
            timestamp=datetime.fromisoformat(msg["timestamp"]),
        ))
    
    # Get created_at from first message
    created_at = datetime.fromisoformat(user_conversations[user_id][conversation_id][0]["timestamp"])
    
    return ConversationHistory(
        conversation_id=conversation_id,
        messages=messages,
        created_at=created_at,
    )


@router.get("/{conversation_id}/status")
async def get_conversation_status(
    conversation_id: str,
    user: User = Depends(get_current_user),
):
    """
    Get the processing status of a conversation.
    
    Returns:
        - processing: Message is being processed by agents
        - completed: Processing finished successfully
        - error: Processing failed
    
    Only returns status for conversations owned by the authenticated user.
    """
    user_id = str(user.id)
    
    if user_id not in user_conversations or conversation_id not in user_conversations[user_id]:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    status = user_pending_tasks.get(user_id, {}).get(conversation_id, {"status": "idle"})
    
    return {
        "conversation_id": conversation_id,
        "status": status.get("status", "idle"),
        "started_at": status.get("started_at"),
        "completed_at": status.get("completed_at"),
        "error": status.get("error"),
    }


@router.get("/", response_model=List[ConversationInfo])
async def list_conversations(user: User = Depends(get_current_user)):
    """
    List all conversations for the authenticated user.
    """
    user_id = str(user.id)
    result = []
    
    if user_id not in user_conversations:
        return result
    
    for conv_id, messages in user_conversations[user_id].items():
        if not messages:
            continue
            
        result.append(ConversationInfo(
            conversation_id=conv_id,
            title=messages[0]["content"][:50] + "..." if len(messages[0]["content"]) > 50 else messages[0]["content"],
            message_count=len(messages),
            created_at=datetime.fromisoformat(messages[0]["timestamp"]),
            last_message_at=datetime.fromisoformat(messages[-1]["timestamp"]) if messages else None,
        ))
    
    return result


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
):
    """
    Delete a conversation owned by the authenticated user.
    """
    user_id = str(user.id)
    
    if user_id not in user_conversations or conversation_id not in user_conversations[user_id]:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    del user_conversations[user_id][conversation_id]
    if user_id in user_pending_tasks:
        user_pending_tasks[user_id].pop(conversation_id, None)
    
    return {"status": "deleted", "conversation_id": conversation_id}


@router.post("/new", response_model=ConversationInfo)
async def create_conversation(
    request: ConversationCreate,
    user: User = Depends(get_current_user),
):
    """
    Create a new empty conversation for the authenticated user.
    """
    user_id = str(user.id)
    conversation_id = str(uuid.uuid4())
    
    # Initialize user's conversation storage if new
    if user_id not in user_conversations:
        user_conversations[user_id] = {}
    
    user_conversations[user_id][conversation_id] = []
    
    return ConversationInfo(
        conversation_id=conversation_id,
        title=request.title,
        message_count=0,
        created_at=datetime.now(),
        last_message_at=None,
    )
