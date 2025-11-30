import { create } from 'zustand';
import type { AgentStatus, ToolCallLog } from '@/types/api';
import type { ProgressEvent } from '@/types/websocket';
import { generateId } from '@/lib/utils';

interface StatusState {
  // Connection state
  isConnected: boolean;
  connectionStatus: 'disconnected' | 'connecting' | 'connected' | 'error';
  
  // Processing state
  isProcessing: boolean;
  progress: ProgressEvent | null;
  
  // Agent tracking
  agents: AgentStatus[];
  activeAgent: string | null;
  
  // Tool call log
  toolCalls: ToolCallLog[];
  
  // Actions
  setConnected: (connected: boolean) => void;
  setConnectionStatus: (status: StatusState['connectionStatus']) => void;
  setProcessing: (processing: boolean) => void;
  setProgress: (progress: ProgressEvent | null) => void;
  updateAgent: (agent: AgentStatus) => void;
  setActiveAgent: (name: string | null) => void;
  addToolCall: (call: Omit<ToolCallLog, 'id'>) => void;
  updateToolCall: (toolName: string, result: { success: boolean; result_preview?: string }) => void;
  clearToolCalls: () => void;
  reset: () => void;
}

const AGENT_DEFAULTS: AgentStatus[] = [
  { name: 'CryptoMarketAnalyst', emoji: '📊', status: 'idle' },
  { name: 'TechnicalAnalyst', emoji: '📈', status: 'idle' },
  { name: 'ChartingAgent', emoji: '📉', status: 'idle' },
  { name: 'CryptoAnalysisCoder', emoji: '👨‍💻', status: 'idle' },
  { name: 'ReportWriter', emoji: '📝', status: 'idle' },
  { name: 'Executor', emoji: '🖥️', status: 'idle' },
];

export const useStatusStore = create<StatusState>((set) => ({
  isConnected: false,
  connectionStatus: 'disconnected',
  isProcessing: false,
  progress: null,
  agents: [...AGENT_DEFAULTS],
  activeAgent: null,
  toolCalls: [],
  
  setConnected: (connected) => set({ isConnected: connected }),
  
  setConnectionStatus: (status) => set({ 
    connectionStatus: status,
    isConnected: status === 'connected',
  }),
  
  setProcessing: (processing) => set({ isProcessing: processing }),
  
  setProgress: (progress) => set({ progress }),
  
  updateAgent: (agent) => set((state) => ({
    agents: state.agents.map((a) =>
      a.name === agent.name ? { ...a, ...agent } : a
    ),
  })),
  
  setActiveAgent: (name) => set((state) => ({
    activeAgent: name,
    agents: state.agents.map((a) => ({
      ...a,
      status: a.name === name ? 'working' : (a.status === 'working' ? 'completed' : a.status),
    })),
  })),
  
  addToolCall: (call) => set((state) => ({
    toolCalls: [...state.toolCalls, { ...call, id: generateId() }],
  })),
  
  updateToolCall: (toolName, result) => set((state) => ({
    toolCalls: state.toolCalls.map((tc) =>
      tc.tool_name === toolName && tc.success === undefined
        ? { ...tc, ...result }
        : tc
    ),
  })),
  
  clearToolCalls: () => set({ toolCalls: [] }),
  
  reset: () => set({
    isProcessing: false,
    progress: null,
    agents: [...AGENT_DEFAULTS],
    activeAgent: null,
    toolCalls: [],
  }),
}));
