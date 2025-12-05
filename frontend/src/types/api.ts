/**
 * API types matching backend models
 */

// Chat/Conversation types
export interface Attachment {
  id: string;
  label: string;
  url: string;
  type: "chart" | "file";
}

// Content filter error details for UI display
export interface ContentFilterDetails {
  triggered_prompt: string;
  filter_type?: string;
  filter_results?: Record<string, unknown>;
}

// Retry notification info for UI display
export interface RetryInfo {
  retry_count: number;
  max_retries: number;
  filter_type?: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "agent" | "error" | "content_filter_error" | "system";
  content: string;
  timestamp: string;
  agentName?: string;
  agentsUsed?: string[];
  charts?: ChartInfo[];
  attachments?: Attachment[];
  isQuickResult?: boolean;  // True if this was a quick lookup (no multi-agent)
  contentFilterDetails?: ContentFilterDetails;  // Present for content_filter_error messages
  isRetryNotification?: boolean;  // True if this is a retry notification
  retryInfo?: RetryInfo;  // Present for retry notification messages
}

export interface Conversation {
  id: string;
  title?: string;
  messages: Message[];
  createdAt: string;
  lastMessageAt?: string;
}

export interface ConversationInfo {
  conversation_id: string;
  title?: string;
  message_count: number;
  created_at: string;
  last_message_at?: string;
}

// Chart types
export interface ChartInfo {
  chart_id: string;
  url: string;
  symbol: string;
  interval: string;
  created_at?: string;
}

export interface ChartRequest {
  symbol: string;
  interval: string;
  indicators: string[];
  theme: "dark" | "light";
  days?: number;
}

// Agent status
export interface AgentStatus {
  name: string;
  emoji: string;
  status: "idle" | "working" | "completed" | "error";
  lastAction?: string;
  timestamp?: string;
}

// Tool call log entry
export interface ToolCallLog {
  id: string;
  agent: string;
  tool_name: string;
  success?: boolean;
  result_preview?: string;
  timestamp: string;
}

// Exchange status
export interface ExchangeStatus {
  bitget: boolean;
  coingecko: boolean;
}

// Health check responses
export interface HealthResponse {
  status: "healthy" | "degraded" | "unhealthy";
  timestamp: string;
}

export interface ReadinessResponse {
  status: "ready" | "degraded";
  checks: {
    api: boolean;
    llm_provider: string;
    ollama?: boolean;
  };
  timestamp: string;
}

// WebSocket status
export interface WsStatusResponse {
  active_connections: number;
  status: string;
  timestamp: string;
}

// API info
export interface ApiInfo {
  name: string;
  version: string;
  docs: string;
  health: string;
  websocket: string;
  ws_status: string;
}
