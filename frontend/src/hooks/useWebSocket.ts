import { useEffect, useCallback } from 'react';
import { wsService } from '@/services/websocket';
import { useChatStore, useStatusStore, useChartStore } from '@/stores';
import type { ServerEvent } from '@/types/websocket';

export function useWebSocket() {
  // Store actions
  const { addMessage, setLoading } = useChatStore();
  const {
    setConnectionStatus,
    setProcessing,
    setProgress,
    updateAgent,
    setActiveAgent,
    addToolCall,
    updateToolCall,
    reset: resetStatus,
  } = useStatusStore();
  const { addChart } = useChartStore();
  
  // Handle incoming messages
  const handleMessage = useCallback((event: ServerEvent) => {
    switch (event.type) {
      case 'status':
        if (event.status === 'processing') {
          setProcessing(true);
        } else if (event.status === 'idle' || event.status === 'cancelled') {
          setProcessing(false);
          setLoading(false);
        }
        break;
        
      case 'agent_step':
        setActiveAgent(event.agent);
        updateAgent({
          name: event.agent,
          emoji: event.emoji,
          status: event.status,
          lastAction: event.message,
          timestamp: event.timestamp,
        });
        break;
        
      case 'tool_call':
        addToolCall({
          agent: event.agent,
          tool_name: event.tool_name,
          timestamp: event.timestamp,
        });
        break;
        
      case 'tool_result':
        updateToolCall(event.tool_name, {
          success: event.success,
          result_preview: event.result_preview,
        });
        break;
        
      case 'chart':
        addChart({
          chart_id: event.chart_id,
          url: event.url,
          symbol: event.symbol,
          interval: '',
          created_at: event.timestamp,
        });
        break;
        
      case 'progress':
        setProgress(event);
        break;
        
      case 'result':
        addMessage({
          role: 'assistant',
          content: event.content,
          timestamp: event.timestamp,
          agentsUsed: event.agents_used,
        });
        setProcessing(false);
        setLoading(false);
        resetStatus();
        break;
        
      case 'error':
        addMessage({
          role: 'error',
          content: event.message + (event.details ? `\n\n${event.details}` : ''),
          timestamp: event.timestamp,
        });
        if (!event.recoverable) {
          setProcessing(false);
          setLoading(false);
        }
        break;
    }
  }, [
    addMessage, setLoading, setProcessing, setProgress,
    updateAgent, setActiveAgent, addToolCall, updateToolCall,
    addChart, resetStatus
  ]);
  
  // Initialize WebSocket connection
  useEffect(() => {
    // Set up handlers
    wsService.setHandlers({
      onStatusChange: setConnectionStatus,
      onMessage: handleMessage,
      onOpen: () => {
        console.log('WebSocket connected to backend');
      },
      onClose: () => {
        console.log('WebSocket disconnected');
        setProcessing(false);
      },
    });
    
    // Connect if not already connected
    wsService.connect();
    
    // Cleanup - but don't disconnect in dev mode due to Strict Mode double-invoke
    // The service will handle reconnection automatically
    return () => {
      // Only disconnect if the window is actually unloading
      // This prevents React Strict Mode from breaking the connection
      if (document.visibilityState === 'hidden') {
        wsService.disconnect();
      }
    };
  }, [handleMessage, setConnectionStatus, setProcessing]);
  
  // Send a chat message
  const sendMessage = useCallback((message: string, conversationId?: string) => {
    // Add user message to chat
    addMessage({
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    });
    
    // Set loading state
    setLoading(true);
    setProcessing(true);
    
    // Send via WebSocket
    wsService.sendChat(message, conversationId);
  }, [addMessage, setLoading, setProcessing]);
  
  // Cancel current processing
  const cancelProcessing = useCallback(() => {
    wsService.sendCancel();
  }, []);
  
  return {
    sendMessage,
    cancelProcessing,
    isConnected: wsService.isConnected,
  };
}

export default useWebSocket;
