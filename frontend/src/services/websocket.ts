import type { ServerEvent, ClientMessage } from '@/types/websocket';

export type WebSocketStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface WebSocketHandlers {
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
  onMessage?: (event: ServerEvent) => void;
  onStatusChange?: (status: WebSocketStatus) => void;
}

// Determine WebSocket URL based on environment
function getWebSocketUrl(): string {
  // Check for environment variable first
  if (import.meta.env.VITE_WS_URL) {
    console.log('[WS] Using VITE_WS_URL:', import.meta.env.VITE_WS_URL);
    return import.meta.env.VITE_WS_URL;
  }
  
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host; // includes port
  const href = window.location.href;
  
  console.log('[WS] Location:', { protocol, host, href });
  
  // For local development with VS Code port forwarding:
  // Frontend runs on 5173, backend on 8000
  // We need to connect to backend directly since Vite proxy doesn't work through port forwarding
  let wsHost = host;
  
  // Check if this is a Codespaces/forwarded URL (contains port number in subdomain)
  const codespaceMatch = host.match(/^(.+)-(\d+)(\.app\.github\.dev.*)$/);
  if (codespaceMatch) {
    // Replace frontend port (5173) with backend port (8500)
    wsHost = `${codespaceMatch[1]}-8500${codespaceMatch[3]}`;
    console.log('[WS] Codespaces detected, switching to backend port:', wsHost);
  } else if (host.match(/localhost:\d+/) || host.match(/127\.0\.0\.1:\d+/)) {
    // Local development - switch to backend port (8500)
    wsHost = host.replace(/:\d+/, ':8500');
    console.log('[WS] Local dev detected, switching to backend port:', wsHost);
  }
  
  const url = `${protocol}//${wsHost}/ws/stream`;
  console.log('[WS] Final WebSocket URL:', url);
  return url;
}

export class WebSocketService {
  private ws: WebSocket | null = null;
  private handlers: WebSocketHandlers = {};
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private url: string;
  private currentStatus: WebSocketStatus = 'disconnected';
  
  constructor(url?: string) {
    this.url = url || getWebSocketUrl();
    console.log('[WS] WebSocket URL:', this.url);
  }
  
  setHandlers(handlers: WebSocketHandlers) {
    this.handlers = handlers;
  }
  
  private updateStatus(status: WebSocketStatus) {
    this.currentStatus = status;
    this.handlers.onStatusChange?.(status);
  }
  
  connect() {
    // If already connected or connecting, don't create another connection
    if (this.ws) {
      if (this.ws.readyState === WebSocket.OPEN) {
        console.log('[WS] Already connected');
        return;
      }
      if (this.ws.readyState === WebSocket.CONNECTING) {
        console.log('[WS] Already connecting');
        return;
      }
      // Close stale connection
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.close();
    }
    
    // Reset reconnect attempts on new connection attempt
    this.reconnectAttempts = 0;
    
    this.updateStatus('connecting');
    console.log('%c[WS] Attempting connection...', 'color: blue; font-weight: bold');
    console.log('[WS] URL:', this.url);
    
    try {
      this.ws = new WebSocket(this.url);
      console.log('[WS] WebSocket object created');
    } catch (e) {
      console.error('[WS] Failed to create WebSocket:', e);
      this.updateStatus('error');
      return;
    }
    
    this.ws.onopen = () => {
      console.log('%c[WS] Connected!', 'color: green; font-weight: bold');
      this.reconnectAttempts = 0;
      this.updateStatus('connected');
      this.handlers.onOpen?.();
      this.startPingInterval();
    };
    
    this.ws.onclose = (event) => {
      console.log('[WS] Closed:', event.code, event.reason);
      this.stopPingInterval();
      this.updateStatus('disconnected');
      this.handlers.onClose?.();
      this.attemptReconnect();
    };
    
    this.ws.onerror = (error) => {
      console.error('[WS] Error:', error);
      this.updateStatus('error');
      this.handlers.onError?.(error);
    };
    
    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as ServerEvent;
        console.log('[WS] Message:', data.type);
        this.handlers.onMessage?.(data);
      } catch (e) {
        console.error('[WS] Failed to parse message:', e);
      }
    };
  }
  
  disconnect() {
    this.stopPingInterval();
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent reconnection
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
  
  send(message: ClientMessage) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.error('[WS] Not connected, cannot send');
    }
  }
  
  sendChat(message: string, conversationId?: string) {
    this.send({
      type: 'chat',
      payload: {
        message,
        conversation_id: conversationId,
      },
    });
  }
  
  sendCancel() {
    this.send({ type: 'cancel', payload: {} });
  }

  sendPing() {
    this.send({ type: 'ping', payload: {} });
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get status(): WebSocketStatus {
    return this.currentStatus;
  }

  private startPingInterval() {
    this.stopPingInterval();
    this.pingInterval = setInterval(() => {
      if (this.isConnected) {
        this.sendPing();
      }
    }, 30000); // Ping every 30 seconds
  }

  private stopPingInterval() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('[WS] Max reconnection attempts reached');
      return;
    }
    
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    setTimeout(() => {
      this.connect();
    }, delay);
  }
}

// Singleton instance - uses getWebSocketUrl() defined above
export const wsService = new WebSocketService();

export default wsService;
