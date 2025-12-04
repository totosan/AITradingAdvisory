"""
WebSocket endpoint for real-time agent streaming.

Enhanced with:
- Improved connection management
- Task cancellation support
- Error recovery
- Heartbeat/ping support
- Agent service integration
"""
import asyncio
import uuid
import json
from datetime import datetime
from typing import Dict, Optional, Set
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.services.agent_service import AgentService

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """
    Manages WebSocket connections with features for:
    - Connection tracking
    - Graceful disconnection
    - Broadcast capabilities
    - Task cancellation
    """
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.agent_services: Dict[str, AgentService] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept and register a new connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections[client_id] = websocket
        logger.info(f"Client {client_id[:8]}... connected. Total: {len(self.active_connections)}")
    
    async def disconnect(self, client_id: str) -> None:
        """Remove a connection and cancel any running tasks."""
        async with self._lock:
            # Cancel running task
            if client_id in self.running_tasks:
                task = self.running_tasks.pop(client_id)
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # Remove connection
            self.active_connections.pop(client_id, None)
        
        logger.info(f"Client {client_id[:8]}... disconnected. Total: {len(self.active_connections)}")
    
    async def send_event(self, client_id: str, event: dict) -> bool:
        """Send an event to a specific client. Returns False if failed."""
        websocket = self.active_connections.get(client_id)
        if not websocket:
            return False
        
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(event)
                return True
        except Exception as e:
            logger.warning(f"Error sending to {client_id[:8]}...: {e}")
            await self.disconnect(client_id)
        return False
    
    async def broadcast(self, event: dict, exclude: Optional[Set[str]] = None) -> None:
        """Broadcast an event to all connected clients."""
        exclude = exclude or set()
        for client_id in list(self.active_connections.keys()):
            if client_id not in exclude:
                await self.send_event(client_id, event)
    
    def register_task(self, client_id: str, task: asyncio.Task) -> None:
        """Register a running task for a client."""
        self.running_tasks[client_id] = task
    
    def register_agent_service(self, client_id: str, agent_service: AgentService) -> None:
        """Register an agent service for a client."""
        self.agent_services[client_id] = agent_service
    
    async def cancel_task(self, client_id: str) -> bool:
        """Cancel a client's running task and signal the agent service."""
        cancelled = False
        
        # First, signal the agent service to cancel (sets internal flag)
        if client_id in self.agent_services:
            agent_service = self.agent_services[client_id]
            await agent_service.cancel()
            logger.info(f"Signalled agent service cancellation for {client_id[:8]}...")
            cancelled = True
        
        # Then cancel the asyncio task
        if client_id in self.running_tasks:
            task = self.running_tasks.pop(client_id)
            if not task.done():
                task.cancel()
                cancelled = True
        
        return cancelled
    
    def cleanup_agent_service(self, client_id: str) -> None:
        """Remove the agent service reference for a client."""
        self.agent_services.pop(client_id, None)
    
    @property
    def connection_count(self) -> int:
        return len(self.active_connections)



manager = ConnectionManager()


async def process_chat_message(
    client_id: str,
    message: str,
    agent_service: AgentService,
    manager: ConnectionManager,
) -> None:
    """Process a chat message and stream responses."""
    try:
        async for event in agent_service.run_streaming(message):
            # Convert Pydantic model to dict if needed
            event_dict = event.model_dump() if hasattr(event, 'model_dump') else event
            
            # Ensure timestamp is serializable
            if 'timestamp' in event_dict and hasattr(event_dict['timestamp'], 'isoformat'):
                event_dict['timestamp'] = event_dict['timestamp'].isoformat()
            
            success = await manager.send_event(client_id, event_dict)
            if not success:
                logger.warning(f"Failed to send event to {client_id[:8]}..., client disconnected")
                break  # Client disconnected
    
    except asyncio.CancelledError:
        await manager.send_event(client_id, {
            "type": "status",
            "status": "cancelled",
            "message": "Task cancelled by user",
            "timestamp": datetime.now().isoformat(),
        })
        logger.info(f"Task cancelled for {client_id[:8]}...")
    except Exception as e:
        logger.exception(f"Error processing chat for {client_id[:8]}...: {e}")
        await manager.send_event(client_id, {
            "type": "error",
            "message": str(e),
            "details": type(e).__name__,
            "recoverable": True,
            "timestamp": datetime.now().isoformat(),
        })


@router.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for agent streaming.
    
    Protocol:
    - Client sends: {"type": "chat", "payload": {"message": "..."}}
    - Client sends: {"type": "cancel", "payload": {}}
    - Client sends: {"type": "ping", "payload": {}}
    - Server sends: AgentStepEvent, ToolCallEvent, ResultEvent, etc.
    """
    client_id = str(uuid.uuid4())
    await manager.connect(websocket, client_id)
    
    # Send connection confirmation
    await manager.send_event(client_id, {
        "type": "status",
        "status": "connected",
        "message": f"Connected to agent service",
        "timestamp": datetime.now().isoformat(),
    })
    
    agent_service = AgentService()
    manager.register_agent_service(client_id, agent_service)
    
    try:
        while True:
            # Wait for message from client with timeout
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=300.0  # 5 minute timeout
                )
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await manager.send_event(client_id, {
                    "type": "ping",
                    "timestamp": datetime.now().isoformat(),
                })
                continue
            
            msg_type = data.get("type")
            payload = data.get("payload", {})
            
            if msg_type == "chat":
                message = payload.get("message", "").strip()
                if not message:
                    await manager.send_event(client_id, {
                        "type": "error",
                        "message": "Empty message",
                        "recoverable": True,
                        "timestamp": datetime.now().isoformat(),
                    })
                    continue
                
                # Reset cancellation flag for new request
                agent_service.reset_cancellation()
                
                # Notify processing started
                await manager.send_event(client_id, {
                    "type": "status",
                    "status": "processing",
                    "message": f"Processing: {message[:50]}...",
                    "timestamp": datetime.now().isoformat(),
                })
                
                # Create task for processing
                task = asyncio.create_task(
                    process_chat_message(client_id, message, agent_service, manager)
                )
                manager.register_task(client_id, task)
                
                # Wait for task to complete
                try:
                    await task
                except asyncio.CancelledError:
                    pass  # Already handled in process_chat_message
                
                # Send idle status
                await manager.send_event(client_id, {
                    "type": "status",
                    "status": "idle",
                    "message": "Ready for next query",
                    "timestamp": datetime.now().isoformat(),
                })
            
            elif msg_type == "cancel":
                cancelled = await manager.cancel_task(client_id)
                await manager.send_event(client_id, {
                    "type": "status",
                    "status": "cancelled" if cancelled else "idle",
                    "message": "Task cancelled" if cancelled else "No task to cancel",
                    "success": cancelled,
                    "timestamp": datetime.now().isoformat(),
                })
            
            elif msg_type == "ping":
                await manager.send_event(client_id, {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat(),
                })
            
            else:
                await manager.send_event(client_id, {
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                    "recoverable": True,
                    "timestamp": datetime.now().isoformat(),
                })
    
    except WebSocketDisconnect:
        logger.info(f"Client {client_id[:8]}... disconnected normally")
    except Exception as e:
        logger.exception(f"WebSocket error for {client_id[:8]}...: {e}")
    finally:
        manager.cleanup_agent_service(client_id)
        await manager.disconnect(client_id)


@router.get("/ws/status")
async def websocket_status():
    """Get WebSocket server status."""
    return {
        "active_connections": manager.connection_count,
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }
