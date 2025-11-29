# Phase 3: Real-time Communication

## Overview

Implement robust WebSocket communication between frontend and backend for real-time agent updates.

---

## 3.1 Connection Architecture

```
┌─────────────────┐     WebSocket      ┌─────────────────┐
│   React App     │ ←───────────────→  │   FastAPI       │
│                 │                    │                 │
│  useWebSocket() │     Events         │  ConnectionMgr  │
│  ├─ connect()   │  ←──────────────   │  ├─ connect()   │
│  ├─ sendChat()  │  ───────────────→  │  ├─ broadcast() │
│  └─ cancel()    │                    │  └─ handle()    │
└─────────────────┘                    └─────────────────┘
        │                                      │
        │                                      │
        ▼                                      ▼
┌─────────────────┐                    ┌─────────────────┐
│  Zustand Stores │                    │  AgentService   │
│  ├─ chatStore   │                    │  run_streaming()│
│  ├─ statusStore │                    └─────────────────┘
│  └─ chartStore  │
└─────────────────┘
```

---

## 3.2 Enhanced Backend WebSocket Handler

```python
# backend/app/api/websocket/stream.py
"""
Enhanced WebSocket handler with connection management and error recovery.
"""
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Optional, Set
from contextlib import asynccontextmanager

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from starlette.websockets import WebSocketState

from app.models.events import *
from app.services.agent_service import AgentService
from app.core.config import get_settings

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
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept and register a new connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections[client_id] = websocket
        print(f"Client {client_id[:8]}... connected. Total: {len(self.active_connections)}")
    
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
        
        print(f"Client {client_id[:8]}... disconnected. Total: {len(self.active_connections)}")
    
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
            print(f"Error sending to {client_id[:8]}...: {e}")
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
    
    async def cancel_task(self, client_id: str) -> bool:
        """Cancel a client's running task."""
        if client_id in self.running_tasks:
            task = self.running_tasks.pop(client_id)
            if not task.done():
                task.cancel()
                return True
        return False


manager = ConnectionManager()


async def process_chat_message(
    websocket: WebSocket,
    client_id: str,
    message: str,
    agent_service: AgentService,
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
                break  # Client disconnected
    
    except asyncio.CancelledError:
        await manager.send_event(client_id, {
            "type": "cancelled",
            "message": "Task cancelled",
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        await manager.send_event(client_id, {
            "type": "error",
            "message": str(e),
            "details": type(e).__name__,
            "timestamp": datetime.now().isoformat(),
        })


@router.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for agent streaming.
    
    Protocol:
    - Client sends: {"type": "chat", "payload": {"message": "..."}}
    - Client sends: {"type": "cancel", "payload": {}}
    - Server sends: AgentStepEvent, ToolCallEvent, ResultEvent, etc.
    """
    client_id = str(uuid.uuid4())
    await manager.connect(websocket, client_id)
    
    agent_service = AgentService()
    
    try:
        while True:
            # Wait for message from client
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=300.0  # 5 minute timeout
                )
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await manager.send_event(client_id, {"type": "ping"})
                continue
            
            msg_type = data.get("type")
            payload = data.get("payload", {})
            
            if msg_type == "chat":
                message = payload.get("message", "").strip()
                if not message:
                    await manager.send_event(client_id, {
                        "type": "error",
                        "message": "Empty message",
                        "timestamp": datetime.now().isoformat(),
                    })
                    continue
                
                # Create task for processing
                task = asyncio.create_task(
                    process_chat_message(websocket, client_id, message, agent_service)
                )
                manager.register_task(client_id, task)
                
                # Wait for task to complete
                await task
            
            elif msg_type == "cancel":
                cancelled = await manager.cancel_task(client_id)
                await manager.send_event(client_id, {
                    "type": "cancelled",
                    "success": cancelled,
                    "timestamp": datetime.now().isoformat(),
                })
            
            elif msg_type == "ping":
                await manager.send_event(client_id, {"type": "pong"})
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error for {client_id[:8]}...: {e}")
    finally:
        await manager.disconnect(client_id)
```

---

## 3.3 Enhanced Frontend WebSocket Hook

```typescript
// frontend/src/hooks/useWebSocket.ts
import { useCallback, useEffect, useRef, useState } from 'react';
import type { ServerEvent, ClientMessage } from '@/types/websocket';
import { useChatStore } from '@/stores/chatStore';
import { useStatusStore } from '@/stores/statusStore';
import { useChartStore } from '@/stores/chartStore';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

interface UseWebSocketOptions {
  reconnectAttempts?: number;
  reconnectInterval?: number;
  heartbeatInterval?: number;
}

export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    reconnectAttempts = 5,
    reconnectInterval = 2000,
    heartbeatInterval = 30000,
  } = options;

  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [error, setError] = useState<string | null>(null);
  
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number>();
  const heartbeatRef = useRef<number>();
  const reconnectCountRef = useRef(0);
  
  const { addMessage, setLoading } = useChatStore();
  const { setAgentStatus, setActiveAgent, addToolCall, setProgress, reset } = useStatusStore();
  const { addChart } = useChartStore();
  
  // Event handler with proper type handling
  const handleEvent = useCallback((event: ServerEvent) => {
    switch (event.type) {
      case 'agent_step':
        setActiveAgent(event.agent);
        setAgentStatus(event.agent, {
          name: event.agent,
          emoji: event.emoji,
          status: event.status === 'working' ? 'working' : 'completed',
        });
        break;
        
      case 'tool_call':
        addToolCall(event);
        setAgentStatus(event.agent, {
          name: event.agent,
          emoji: '🔧',
          status: 'working',
          lastAction: `Calling ${event.tool_name}`,
        });
        break;
        
      case 'tool_result':
        // Could show tool result in status
        break;
        
      case 'progress':
        setProgress(event.current_turn, event.max_turns);
        break;
        
      case 'chart':
        addChart({
          id: event.chart_id,
          url: event.url,
          symbol: event.symbol,
          interval: '1H',
        });
        // Notify user
        console.log(`📈 Chart generated: ${event.url}`);
        break;
        
      case 'result':
        addMessage({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: event.content,
          timestamp: event.timestamp,
          agentsUsed: event.agents_used,
        });
        setLoading(false);
        reset();
        break;
        
      case 'error':
        addMessage({
          id: crypto.randomUUID(),
          role: 'assistant',
          content: `❌ **Error:** ${event.message}\n\n${event.details || ''}`,
          timestamp: event.timestamp,
        });
        setLoading(false);
        reset();
        setError(event.message);
        break;
        
      case 'cancelled':
        setLoading(false);
        reset();
        break;
        
      case 'pong':
        // Heartbeat response received
        break;
    }
  }, [addMessage, setLoading, setActiveAgent, setAgentStatus, addToolCall, setProgress, addChart, reset]);
  
  // Start heartbeat to keep connection alive
  const startHeartbeat = useCallback(() => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
    }
    
    heartbeatRef.current = window.setInterval(() => {
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(JSON.stringify({ type: 'ping', payload: {} }));
      }
    }, heartbeatInterval);
  }, [heartbeatInterval]);
  
  // Stop heartbeat
  const stopHeartbeat = useCallback(() => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = undefined;
    }
  }, []);
  
  // Connect to WebSocket
  const connect = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      return;
    }
    
    setStatus('connecting');
    setError(null);
    
    try {
      const ws = new WebSocket(`${WS_URL}/ws/stream`);
      
      ws.onopen = () => {
        setStatus('connected');
        setError(null);
        reconnectCountRef.current = 0;
        console.log('🔌 WebSocket connected');
        startHeartbeat();
      };
      
      ws.onclose = (event) => {
        setStatus('disconnected');
        stopHeartbeat();
        
        // Only reconnect if not a clean close
        if (!event.wasClean && reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current++;
          console.log(`🔄 Reconnecting... (${reconnectCountRef.current}/${reconnectAttempts})`);
          
          reconnectTimeoutRef.current = window.setTimeout(
            connect,
            reconnectInterval * reconnectCountRef.current // Exponential backoff
          );
        } else if (reconnectCountRef.current >= reconnectAttempts) {
          setError('Failed to connect after multiple attempts');
          setStatus('error');
        }
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setError('Connection error');
      };
      
      ws.onmessage = (event) => {
        try {
          const data: ServerEvent = JSON.parse(event.data);
          handleEvent(data);
        } catch (e) {
          console.error('Failed to parse message:', e);
        }
      };
      
      socketRef.current = ws;
    } catch (e) {
      setError(`Failed to create WebSocket: ${e}`);
      setStatus('error');
    }
  }, [handleEvent, reconnectAttempts, reconnectInterval, startHeartbeat, stopHeartbeat]);
  
  // Disconnect
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    stopHeartbeat();
    
    if (socketRef.current) {
      socketRef.current.close(1000, 'User disconnected');
      socketRef.current = null;
    }
    
    setStatus('disconnected');
    reconnectCountRef.current = 0;
  }, [stopHeartbeat]);
  
  // Send message
  const send = useCallback((message: ClientMessage): boolean => {
    if (socketRef.current?.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected');
      return false;
    }
    
    try {
      socketRef.current.send(JSON.stringify(message));
      return true;
    } catch (e) {
      console.error('Failed to send message:', e);
      return false;
    }
  }, []);
  
  // Send chat message
  const sendChat = useCallback((message: string) => {
    if (!message.trim()) return false;
    
    setLoading(true);
    reset();
    
    // Add user message immediately
    addMessage({
      id: crypto.randomUUID(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    });
    
    return send({ type: 'chat', payload: { message: message.trim() } });
  }, [send, setLoading, reset, addMessage]);
  
  // Cancel current task
  const cancelTask = useCallback(() => {
    const success = send({ type: 'cancel', payload: {} });
    if (success) {
      setLoading(false);
      reset();
    }
    return success;
  }, [send, setLoading, reset]);
  
  // Auto-connect on mount
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);
  
  return {
    status,
    error,
    connect,
    disconnect,
    sendChat,
    cancelTask,
    isConnected: status === 'connected',
  };
}
```

---

## 3.4 Reconnection Handling Component

```tsx
// frontend/src/components/ConnectionStatus.tsx
import { useWebSocket } from '@/hooks/useWebSocket';
import { Button } from './ui/button';
import { Wifi, WifiOff, AlertCircle, RefreshCw } from 'lucide-react';

export function ConnectionStatus() {
  const { status, error, connect, isConnected } = useWebSocket();
  
  if (isConnected) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-green-500">
        <Wifi className="h-3.5 w-3.5" />
        <span>Connected</span>
      </div>
    );
  }
  
  if (status === 'connecting') {
    return (
      <div className="flex items-center gap-1.5 text-xs text-yellow-500">
        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
        <span>Connecting...</span>
      </div>
    );
  }
  
  if (status === 'error') {
    return (
      <div className="flex items-center gap-2 text-xs text-red-500">
        <AlertCircle className="h-3.5 w-3.5" />
        <span>{error || 'Connection failed'}</span>
        <Button variant="ghost" size="sm" onClick={connect} className="h-6 px-2">
          Retry
        </Button>
      </div>
    );
  }
  
  return (
    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <WifiOff className="h-3.5 w-3.5" />
      <span>Disconnected</span>
      <Button variant="ghost" size="sm" onClick={connect} className="h-6 px-2">
        Connect
      </Button>
    </div>
  );
}
```

---

## 3.5 Message Queue for Reliability

For handling messages when reconnecting:

```typescript
// frontend/src/services/messageQueue.ts
interface QueuedMessage {
  id: string;
  message: ClientMessage;
  timestamp: number;
  retries: number;
}

class MessageQueue {
  private queue: QueuedMessage[] = [];
  private maxRetries = 3;
  private maxAge = 60000; // 1 minute
  
  add(message: ClientMessage): string {
    const id = crypto.randomUUID();
    this.queue.push({
      id,
      message,
      timestamp: Date.now(),
      retries: 0,
    });
    return id;
  }
  
  remove(id: string): void {
    this.queue = this.queue.filter(m => m.id !== id);
  }
  
  getNext(): QueuedMessage | undefined {
    // Clean old messages
    this.queue = this.queue.filter(
      m => Date.now() - m.timestamp < this.maxAge && m.retries < this.maxRetries
    );
    
    return this.queue[0];
  }
  
  markRetry(id: string): void {
    const msg = this.queue.find(m => m.id === id);
    if (msg) {
      msg.retries++;
    }
  }
  
  clear(): void {
    this.queue = [];
  }
  
  get length(): number {
    return this.queue.length;
  }
}

export const messageQueue = new MessageQueue();
```

---

## 3.6 Testing WebSocket Connection

```typescript
// frontend/src/__tests__/websocket.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useWebSocket } from '../hooks/useWebSocket';

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  
  onopen: (() => void) | null = null;
  onclose: ((event: any) => void) | null = null;
  onmessage: ((event: any) => void) | null = null;
  onerror: ((event: any) => void) | null = null;
  readyState = WebSocket.CONNECTING;
  
  constructor(public url: string) {
    MockWebSocket.instances.push(this);
  }
  
  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.({ wasClean: true });
  });
  
  // Simulate opening connection
  simulateOpen() {
    this.readyState = WebSocket.OPEN;
    this.onopen?.();
  }
  
  // Simulate receiving a message
  simulateMessage(data: any) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }
}

describe('useWebSocket', () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    (global as any).WebSocket = MockWebSocket;
  });
  
  afterEach(() => {
    MockWebSocket.instances.forEach(ws => ws.close());
  });
  
  it('connects on mount', async () => {
    const { result } = renderHook(() => useWebSocket());
    
    expect(result.current.status).toBe('connecting');
    
    // Simulate connection open
    MockWebSocket.instances[0].simulateOpen();
    
    await waitFor(() => {
      expect(result.current.status).toBe('connected');
    });
  });
  
  it('sends chat messages', async () => {
    const { result } = renderHook(() => useWebSocket());
    
    MockWebSocket.instances[0].simulateOpen();
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });
    
    act(() => {
      result.current.sendChat('Analyze Bitcoin');
    });
    
    expect(MockWebSocket.instances[0].send).toHaveBeenCalledWith(
      JSON.stringify({
        type: 'chat',
        payload: { message: 'Analyze Bitcoin' }
      })
    );
  });
  
  it('handles agent events', async () => {
    const { result } = renderHook(() => useWebSocket());
    
    MockWebSocket.instances[0].simulateOpen();
    
    await waitFor(() => {
      expect(result.current.isConnected).toBe(true);
    });
    
    // Simulate agent step event
    MockWebSocket.instances[0].simulateMessage({
      type: 'agent_step',
      agent: 'CryptoMarketAnalyst',
      emoji: '📊',
      status: 'working',
      timestamp: new Date().toISOString(),
    });
    
    // Check that status store was updated
    // (would need to mock or check the store directly)
  });
});
```

---

## Next Steps

After completing Phase 3, proceed to:
- [Phase 4: Secrets Management](./PHASE_4_SECRETS.md)

---

*Document created: 2025-11-29*
