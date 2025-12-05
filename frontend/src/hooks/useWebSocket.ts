import { useEffect, useCallback } from 'react';
import { wsService } from '@/services/websocket';
import { useChatStore, useStatusStore, useChartStore } from '@/stores';
import type { ServerEvent } from '@/types/websocket';
import type { Attachment } from '@/types/api';

const normalizeChartUrl = (rawUrl: string) => {
  if (!rawUrl) return '';
  if (/^https?:\/\//i.test(rawUrl)) {
    return rawUrl;
  }

  let url = rawUrl;
  if (url.startsWith('/app/')) {
    url = url.replace('/app', '');
  }

  if (url.startsWith('/outputs/charts/')) {
    url = url.replace('/outputs/charts/', '/charts/');
  }

  if (!url.startsWith('/')) {
    url = `/${url}`;
  }

  return url;
};

const buildChartAttachmentFromEvent = (event: {
  chart_id: string;
  symbol: string;
  interval?: string;
  url: string;
}): Attachment => ({
  id: event.chart_id,
  label: `${event.symbol} ${event.interval || ''}`.trim() || 'Chart',
  url: normalizeChartUrl(event.url),
  type: 'chart',
});

const chartPathRegex = /(\/app)?\/outputs\/charts\/([\w\-]+\.html)/gi;

const extractChartAttachmentsFromContent = (content: string): Attachment[] => {
  const attachments: Attachment[] = [];
  let match: RegExpExecArray | null;

  while ((match = chartPathRegex.exec(content)) !== null) {
    const filename = match[2];
    attachments.push({
      id: filename,
      label: filename.replace(/\.html$/i, ''),
      url: normalizeChartUrl(`/charts/${filename}`),
      type: 'chart',
    });
  }

  return attachments;
};

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
        
      case 'chart': {
        const attachment = buildChartAttachmentFromEvent(event);
        addChart({
          chart_id: event.chart_id,
          url: attachment.url,
          symbol: event.symbol,
          interval: event.interval || '',
          created_at: event.timestamp,
        });
        addMessage({
          role: 'assistant',
          content: `Chart generated for ${event.symbol} (${event.interval || 'custom'}).`,
          timestamp: event.timestamp,
          attachments: [attachment],
        });
        break;
      }
        
      case 'progress':
        setProgress(event);
        break;
        
      case 'result': {
        const attachments = extractChartAttachmentsFromContent(event.content);
        attachments.forEach((attachment) => {
          // Attempt to derive symbol/interval from filename (best effort)
          const base = attachment.label;
          const parts = base.split('_');
          const symbol = parts[0] || 'Chart';
          const interval = parts[1] || 'custom';

          addChart({
            chart_id: attachment.id,
            url: attachment.url,
            symbol,
            interval,
            created_at: event.timestamp,
          });
        });

        addMessage({
          role: 'assistant',
          content: event.content,
          timestamp: event.timestamp,
          agentsUsed: event.agents_used,
          attachments: attachments.length ? attachments : undefined,
        });
        setProcessing(false);
        setLoading(false);
        resetStatus();
        break;
      }
      
      case 'quick_result':
        // Quick result from intent routing - no multi-agent processing
        addMessage({
          role: 'assistant',
          content: event.content,
          timestamp: event.timestamp,
          agentsUsed: [], // No agents used for quick lookups
          isQuickResult: true,
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
      
      case 'content_filter_error':
        // Special handling for content filter errors with prompt display
        addMessage({
          role: 'content_filter_error',
          content: event.message,
          timestamp: event.timestamp,
          contentFilterDetails: {
            triggered_prompt: event.triggered_prompt,
            filter_type: event.filter_type,
            filter_results: event.filter_results,
          },
        });
        setProcessing(false);
        setLoading(false);
        break;
      
      case 'content_filter_retry':
        // Show a status message that retry is happening
        addMessage({
          role: 'system',
          content: `⏳ ${event.message}`,
          timestamp: event.timestamp,
          isRetryNotification: true,
          retryInfo: {
            retry_count: event.retry_count,
            max_retries: event.max_retries,
            filter_type: event.filter_type,
          },
        });
        // Don't stop processing - we're still working
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
