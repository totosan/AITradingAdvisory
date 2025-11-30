"""
WebSocket endpoint for real-time agent streaming.
"""
import asyncio
import uuid
import json
from datetime import datetime
from typing import Dict, Optional
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._active_tasks: Dict[str, Optional[asyncio.Task]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self._active_tasks[client_id] = None
        logger.info(f"Client {client_id} connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)
        task = self._active_tasks.pop(client_id, None)
        if task and not task.done():
            task.cancel()
        logger.info(f"Client {client_id} disconnected. Remaining: {len(self.active_connections)}")
    
    async def send_json(self, client_id: str, data: dict) -> bool:
        websocket = self.active_connections.get(client_id)
        if not websocket:
            return False
        try:
            await websocket.send_json(data)
            return True
        except Exception as e:
            logger.warning(f"Failed to send to {client_id}: {e}")
            return False
    
    def cancel_task(self, client_id: str) -> bool:
        task = self._active_tasks.get(client_id)
        if task and not task.done():
            task.cancel()
            return True
        return False
    
    @property
    def connection_count(self) -> int:
        return len(self.active_connections)


manager = ConnectionManager()


@router.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for streaming agent interactions."""
    client_id = str(uuid.uuid4())
    
    await manager.connect(websocket, client_id)
    
    # Send connection confirmation
    await manager.send_json(client_id, {
        "type": "status",
        "status": "connected",
        "message": f"Connected as {client_id}",
        "timestamp": datetime.now().isoformat(),
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "ping":
                await manager.send_json(client_id, {
                    "type": "pong",
                    "timestamp": datetime.now().isoformat(),
                })
            
            elif message_type == "cancel":
                cancelled = manager.cancel_task(client_id)
                await manager.send_json(client_id, {
                    "type": "status",
                    "status": "cancelled" if cancelled else "idle",
                    "message": "Task cancelled" if cancelled else "No task to cancel",
                    "timestamp": datetime.now().isoformat(),
                })
            
            elif message_type == "chat":
                message = data.get("message", "").strip()
                
                if not message:
                    await manager.send_json(client_id, {
                        "type": "error",
                        "message": "Empty message",
                        "recoverable": True,
                        "timestamp": datetime.now().isoformat(),
                    })
                    continue
                
                # Notify processing started
                await manager.send_json(client_id, {
                    "type": "status",
                    "status": "processing",
                    "message": f"Processing: {message[:50]}...",
                    "timestamp": datetime.now().isoformat(),
                })
                
                # For now, just echo back a result
                # TODO: Integrate with AgentService
                await manager.send_json(client_id, {
                    "type": "result",
                    "content": f"**Echo:** {message}\n\n_Agent integration coming soon..._",
                    "format": "markdown",
                    "agents_used": ["Echo"],
                    "timestamp": datetime.now().isoformat(),
                })
                
                await manager.send_json(client_id, {
                    "type": "status",
                    "status": "idle",
                    "message": "Ready",
                    "timestamp": datetime.now().isoformat(),
                })
            
            else:
                await manager.send_json(client_id, {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                    "recoverable": True,
                    "timestamp": datetime.now().isoformat(),
                })
    
    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected normally")
    except Exception as e:
        logger.exception(f"WebSocket error for {client_id}: {e}")
    finally:
        manager.disconnect(client_id)


@router.get("/ws/status")
async def websocket_status():
    """Get WebSocket server status."""
    return {
        "active_connections": manager.connection_count,
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
    }
