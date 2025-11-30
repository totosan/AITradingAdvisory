/**
 * WebSocket event types matching backend/app/models/events.py
 */

export type EventType =
  | "status"
  | "agent_step"
  | "tool_call"
  | "tool_result"
  | "chart"
  | "result"
  | "error"
  | "progress";

export interface StatusEvent {
  type: "status";
  status: "connected" | "processing" | "idle" | "cancelled" | "disconnecting";
  message?: string;
  timestamp: string;
}

export interface AgentStepEvent {
  type: "agent_step";
  agent: string;
  emoji: string;
  status: "working" | "completed" | "error";
  message?: string;
  timestamp: string;
}

export interface ToolCallEvent {
  type: "tool_call";
  agent: string;
  tool_name: string;
  arguments?: Record<string, unknown>;
  timestamp: string;
}

export interface ToolResultEvent {
  type: "tool_result";
  tool_name: string;
  success: boolean;
  result_preview?: string;
  timestamp: string;
}

export interface ChartEvent {
  type: "chart";
  chart_id: string;
  url: string;
  symbol: string;
  timestamp: string;
}

export interface ResultEvent {
  type: "result";
  content: string;
  format: "markdown" | "text";
  agents_used: string[];
  timestamp: string;
}

export interface ErrorEvent {
  type: "error";
  message: string;
  details?: string;
  recoverable: boolean;
  timestamp: string;
}

export interface ProgressEvent {
  type: "progress";
  current_turn: number;
  max_turns: number;
  percentage: number;
  timestamp: string;
}

export type ServerEvent =
  | StatusEvent
  | AgentStepEvent
  | ToolCallEvent
  | ToolResultEvent
  | ChartEvent
  | ResultEvent
  | ErrorEvent
  | ProgressEvent;

/**
 * Client → Server message types
 */
export interface ChatClientMessage {
  type: "chat";
  message: string;
  conversation_id?: string;
}

export interface CancelClientMessage {
  type: "cancel";
}

export interface PingClientMessage {
  type: "ping";
}

export type ClientMessage =
  | ChatClientMessage
  | CancelClientMessage
  | PingClientMessage;
