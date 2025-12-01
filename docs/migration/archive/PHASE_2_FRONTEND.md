# Phase 2: Frontend Application

> **Status: ✅ Complete (95%)**
> 
> **Completed:** 2025-12-01
> - Vite + React + TypeScript ✅
> - 4-panel layout ✅ (Chat, Status, Results, Charts)
> - TailwindCSS styling ✅
> - Zustand stores ✅ (chat, status, charts)
> - Settings UI ✅ (SettingsDialog with tabs)
> - WebSocket client ✅ (with reconnection)
> - Build verified: 0 TypeScript errors, 438KB JS bundle
> 
> **Remaining:** Mobile responsive polish, export button

## Overview

Create a modern React + TypeScript frontend with a 4-panel layout for the crypto analysis platform.

---

## Step 2.1: Project Setup

### Initialize Vite + React + TypeScript

```bash
cd /path/to/MagenticOne
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

### Install Dependencies

```bash
# UI Components
npm install @radix-ui/react-dialog @radix-ui/react-tabs @radix-ui/react-tooltip
npm install class-variance-authority clsx tailwind-merge
npm install lucide-react

# State Management
npm install zustand

# Data Fetching
npm install @tanstack/react-query axios

# Markdown
npm install react-markdown remark-gfm

# Charting
npm install lightweight-charts

# Styling
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# shadcn/ui setup
npx shadcn@latest init
```

---

## Step 2.2: Tailwind Configuration

```javascript
// frontend/tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        chart: {
          up: "#22c55e",
          down: "#ef4444",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
```

---

## Step 2.3: Project Structure

```
frontend/src/
├── App.tsx
├── main.tsx
├── index.css
├── components/
│   ├── ui/                      # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   ├── input.tsx
│   │   └── ...
│   ├── layout/
│   │   ├── MainLayout.tsx       # Main 4-panel grid
│   │   ├── Header.tsx
│   │   └── PanelContainer.tsx
│   ├── chat/
│   │   ├── ChatBox.tsx
│   │   ├── ChatInput.tsx
│   │   ├── MessageList.tsx
│   │   └── MessageBubble.tsx
│   ├── results/
│   │   ├── ResultsPanel.tsx
│   │   ├── MarkdownRenderer.tsx
│   │   ├── MetricsCard.tsx
│   │   └── DataTable.tsx
│   ├── status/
│   │   ├── StatusPanel.tsx
│   │   ├── AgentCard.tsx
│   │   ├── ToolCallLog.tsx
│   │   └── ProgressBar.tsx
│   ├── charts/
│   │   ├── ChartPanel.tsx
│   │   ├── TradingViewChart.tsx
│   │   ├── ChartControls.tsx
│   │   └── MiniChart.tsx
│   └── settings/
│       ├── SettingsDialog.tsx
│       ├── ExchangeSettings.tsx
│       └── LLMSettings.tsx
├── hooks/
│   ├── useWebSocket.ts
│   ├── useChat.ts
│   └── useAgentStatus.ts
├── stores/
│   ├── chatStore.ts
│   ├── statusStore.ts
│   └── chartStore.ts
├── services/
│   ├── api.ts
│   └── websocket.ts
├── types/
│   ├── api.ts
│   └── websocket.ts
└── lib/
    └── utils.ts
```

---

## Step 2.4: TypeScript Types

```typescript
// frontend/src/types/websocket.ts

export type EventType = 
  | "agent_step" 
  | "tool_call" 
  | "tool_result" 
  | "chart" 
  | "result" 
  | "error" 
  | "progress";

export interface AgentStepEvent {
  type: "agent_step";
  agent: string;
  emoji: string;
  status: "working" | "completed" | "error";
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
  | AgentStepEvent 
  | ToolCallEvent 
  | ToolResultEvent 
  | ChartEvent 
  | ResultEvent 
  | ErrorEvent 
  | ProgressEvent;

export interface ClientMessage {
  type: "chat" | "cancel" | "subscribe";
  payload: {
    message?: string;
    symbols?: string[];
  };
}
```

```typescript
// frontend/src/types/api.ts

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  agentsUsed?: string[];
  charts?: ChartInfo[];
}

export interface ChartInfo {
  id: string;
  url: string;
  symbol: string;
  interval: string;
}

export interface AgentStatus {
  name: string;
  emoji: string;
  status: "idle" | "working" | "completed" | "error";
  lastAction?: string;
}

export interface ExchangeStatus {
  bitget: boolean;
  coingecko: boolean;
}
```

---

## Step 2.5: Zustand Stores

```typescript
// frontend/src/stores/chatStore.ts
import { create } from 'zustand';
import type { Message } from '@/types/api';

interface ChatState {
  messages: Message[];
  isLoading: boolean;
  conversationId: string | null;
  
  addMessage: (message: Message) => void;
  updateLastMessage: (content: string) => void;
  setLoading: (loading: boolean) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isLoading: false,
  conversationId: null,
  
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message],
  })),
  
  updateLastMessage: (content) => set((state) => ({
    messages: state.messages.map((msg, idx) => 
      idx === state.messages.length - 1 
        ? { ...msg, content } 
        : msg
    ),
  })),
  
  setLoading: (loading) => set({ isLoading: loading }),
  
  clearMessages: () => set({ messages: [], conversationId: null }),
}));
```

```typescript
// frontend/src/stores/statusStore.ts
import { create } from 'zustand';
import type { AgentStatus, ToolCallEvent } from '@/types';

interface StatusState {
  agents: Record<string, AgentStatus>;
  activeAgent: string | null;
  toolCalls: ToolCallEvent[];
  progress: number;
  currentTurn: number;
  maxTurns: number;
  
  setAgentStatus: (agent: string, status: AgentStatus) => void;
  setActiveAgent: (agent: string | null) => void;
  addToolCall: (call: ToolCallEvent) => void;
  setProgress: (current: number, max: number) => void;
  reset: () => void;
}

const INITIAL_AGENTS: Record<string, AgentStatus> = {
  CryptoMarketAnalyst: { name: 'CryptoMarketAnalyst', emoji: '📊', status: 'idle' },
  TechnicalAnalyst: { name: 'TechnicalAnalyst', emoji: '📈', status: 'idle' },
  ChartingAgent: { name: 'ChartingAgent', emoji: '📉', status: 'idle' },
  CryptoAnalysisCoder: { name: 'CryptoAnalysisCoder', emoji: '👨‍💻', status: 'idle' },
  ReportWriter: { name: 'ReportWriter', emoji: '📝', status: 'idle' },
  Executor: { name: 'Executor', emoji: '🖥️', status: 'idle' },
};

export const useStatusStore = create<StatusState>((set) => ({
  agents: INITIAL_AGENTS,
  activeAgent: null,
  toolCalls: [],
  progress: 0,
  currentTurn: 0,
  maxTurns: 20,
  
  setAgentStatus: (agent, status) => set((state) => ({
    agents: { ...state.agents, [agent]: status },
  })),
  
  setActiveAgent: (agent) => set({ activeAgent: agent }),
  
  addToolCall: (call) => set((state) => ({
    toolCalls: [...state.toolCalls.slice(-20), call], // Keep last 20
  })),
  
  setProgress: (current, max) => set({
    currentTurn: current,
    maxTurns: max,
    progress: (current / max) * 100,
  }),
  
  reset: () => set({
    agents: INITIAL_AGENTS,
    activeAgent: null,
    toolCalls: [],
    progress: 0,
    currentTurn: 0,
  }),
}));
```

```typescript
// frontend/src/stores/chartStore.ts
import { create } from 'zustand';
import type { ChartInfo } from '@/types/api';

interface ChartState {
  charts: ChartInfo[];
  activeChart: ChartInfo | null;
  symbol: string;
  interval: string;
  indicators: string[];
  
  addChart: (chart: ChartInfo) => void;
  setActiveChart: (chart: ChartInfo | null) => void;
  setSymbol: (symbol: string) => void;
  setInterval: (interval: string) => void;
  toggleIndicator: (indicator: string) => void;
}

export const useChartStore = create<ChartState>((set) => ({
  charts: [],
  activeChart: null,
  symbol: 'BTCUSDT',
  interval: '1H',
  indicators: ['volume'],
  
  addChart: (chart) => set((state) => ({
    charts: [chart, ...state.charts.slice(0, 9)],
    activeChart: chart,
  })),
  
  setActiveChart: (chart) => set({ activeChart: chart }),
  
  setSymbol: (symbol) => set({ symbol }),
  
  setInterval: (interval) => set({ interval }),
  
  toggleIndicator: (indicator) => set((state) => ({
    indicators: state.indicators.includes(indicator)
      ? state.indicators.filter(i => i !== indicator)
      : [...state.indicators, indicator],
  })),
}));
```

---

## Step 2.6: WebSocket Hook

```typescript
// frontend/src/hooks/useWebSocket.ts
import { useCallback, useEffect, useRef, useState } from 'react';
import type { ServerEvent, ClientMessage } from '@/types/websocket';
import { useChatStore } from '@/stores/chatStore';
import { useStatusStore } from '@/stores/statusStore';
import { useChartStore } from '@/stores/chartStore';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export function useWebSocket() {
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected');
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number>();
  
  const { addMessage, updateLastMessage, setLoading } = useChatStore();
  const { setAgentStatus, setActiveAgent, addToolCall, setProgress, reset } = useStatusStore();
  const { addChart } = useChartStore();
  
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
        break;
        
      case 'progress':
        setProgress(event.current_turn, event.max_turns);
        break;
        
      case 'chart':
        addChart({
          id: event.chart_id,
          url: event.url,
          symbol: event.symbol,
          interval: '1H', // Could be included in event
        });
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
          content: `❌ Error: ${event.message}`,
          timestamp: event.timestamp,
        });
        setLoading(false);
        reset();
        break;
    }
  }, [addMessage, setLoading, setActiveAgent, setAgentStatus, addToolCall, setProgress, addChart, reset]);
  
  const connect = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) return;
    
    setStatus('connecting');
    const ws = new WebSocket(`${WS_URL}/ws/stream`);
    
    ws.onopen = () => {
      setStatus('connected');
      console.log('WebSocket connected');
    };
    
    ws.onclose = () => {
      setStatus('disconnected');
      console.log('WebSocket disconnected, reconnecting...');
      reconnectTimeoutRef.current = window.setTimeout(connect, 2000);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    ws.onmessage = (event) => {
      try {
        const data: ServerEvent = JSON.parse(event.data);
        handleEvent(data);
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };
    
    socketRef.current = ws;
  }, [handleEvent]);
  
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    socketRef.current?.close();
    socketRef.current = null;
    setStatus('disconnected');
  }, []);
  
  const send = useCallback((message: ClientMessage) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify(message));
    } else {
      console.error('WebSocket not connected');
    }
  }, []);
  
  const sendChat = useCallback((message: string) => {
    setLoading(true);
    reset();
    addMessage({
      id: crypto.randomUUID(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    });
    send({ type: 'chat', payload: { message } });
  }, [send, setLoading, reset, addMessage]);
  
  const cancelTask = useCallback(() => {
    send({ type: 'cancel', payload: {} });
    setLoading(false);
    reset();
  }, [send, setLoading, reset]);
  
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);
  
  return {
    status,
    connect,
    disconnect,
    sendChat,
    cancelTask,
  };
}
```

---

## Step 2.7: Main Layout Component

```tsx
// frontend/src/components/layout/MainLayout.tsx
import { Header } from './Header';
import { ChatBox } from '../chat/ChatBox';
import { ResultsPanel } from '../results/ResultsPanel';
import { StatusPanel } from '../status/StatusPanel';
import { ChartPanel } from '../charts/ChartPanel';

export function MainLayout() {
  return (
    <div className="h-screen flex flex-col bg-background text-foreground">
      <Header />
      
      <main className="flex-1 grid grid-cols-12 gap-4 p-4 overflow-hidden">
        {/* Left Column - Results, Status, Chat */}
        <div className="col-span-5 flex flex-col gap-4 overflow-hidden">
          {/* Results Panel - Takes most space */}
          <div className="flex-1 min-h-0 overflow-hidden">
            <ResultsPanel />
          </div>
          
          {/* Status Panel */}
          <div className="h-32 shrink-0">
            <StatusPanel />
          </div>
          
          {/* Chat Box */}
          <div className="h-40 shrink-0">
            <ChatBox />
          </div>
        </div>
        
        {/* Right Column - Charts */}
        <div className="col-span-7 overflow-hidden">
          <ChartPanel />
        </div>
      </main>
    </div>
  );
}
```

```tsx
// frontend/src/components/layout/Header.tsx
import { Settings, Moon, Sun } from 'lucide-react';
import { Button } from '../ui/button';
import { SettingsDialog } from '../settings/SettingsDialog';
import { useState } from 'react';

export function Header() {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(true);
  
  const toggleTheme = () => {
    setDarkMode(!darkMode);
    document.documentElement.classList.toggle('dark');
  };
  
  return (
    <header className="h-14 border-b border-border flex items-center justify-between px-6">
      <div className="flex items-center gap-3">
        <span className="text-2xl">🪙</span>
        <h1 className="text-xl font-bold">Crypto Analysis Platform</h1>
        <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
          Powered by MagenticOne
        </span>
      </div>
      
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={toggleTheme}>
          {darkMode ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </Button>
        <Button variant="ghost" size="icon" onClick={() => setSettingsOpen(true)}>
          <Settings className="h-5 w-5" />
        </Button>
      </div>
      
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </header>
  );
}
```

---

## Step 2.8: Chat Components

```tsx
// frontend/src/components/chat/ChatBox.tsx
import { useState, useRef, useEffect } from 'react';
import { Send, StopCircle } from 'lucide-react';
import { Button } from '../ui/button';
import { useChatStore } from '@/stores/chatStore';
import { useWebSocket } from '@/hooks/useWebSocket';

export function ChatBox() {
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const { isLoading, messages } = useChatStore();
  const { sendChat, cancelTask, status } = useWebSocket();
  
  const handleSubmit = () => {
    if (!input.trim() || isLoading) return;
    sendChat(input.trim());
    setInput('');
  };
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };
  
  return (
    <div className="h-full rounded-lg border border-border bg-card p-4 flex flex-col">
      <div className="flex items-center gap-2 mb-2">
        <span className="text-sm font-medium">💬 Chat</span>
        <span className={`text-xs px-2 py-0.5 rounded-full ${
          status === 'connected' ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'
        }`}>
          {status}
        </span>
      </div>
      
      <div className="flex-1 flex gap-2">
        <textarea
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about any cryptocurrency... (e.g., 'Analyze Bitcoin with RSI and MACD')"
          className="flex-1 resize-none bg-background border border-input rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          disabled={isLoading}
        />
        
        {isLoading ? (
          <Button variant="destructive" size="icon" onClick={cancelTask}>
            <StopCircle className="h-5 w-5" />
          </Button>
        ) : (
          <Button size="icon" onClick={handleSubmit} disabled={!input.trim()}>
            <Send className="h-5 w-5" />
          </Button>
        )}
      </div>
    </div>
  );
}
```

---

## Step 2.9: Results Panel

```tsx
// frontend/src/components/results/ResultsPanel.tsx
import { useRef, useEffect } from 'react';
import { useChatStore } from '@/stores/chatStore';
import { MessageBubble } from './MessageBubble';

export function ResultsPanel() {
  const { messages } = useChatStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);
  
  return (
    <div className="h-full rounded-lg border border-border bg-card flex flex-col">
      <div className="px-4 py-3 border-b border-border">
        <span className="text-sm font-medium">📊 Analysis Results</span>
      </div>
      
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            <div className="text-center">
              <p className="text-lg mb-2">👋 Welcome to Crypto Analysis</p>
              <p className="text-sm">Ask about any cryptocurrency to get started!</p>
              <p className="text-xs mt-4 text-muted-foreground">
                Try: "Analyze Bitcoin" or "Compare ETH vs SOL"
              </p>
            </div>
          </div>
        ) : (
          messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))
        )}
      </div>
    </div>
  );
}
```

```tsx
// frontend/src/components/results/MessageBubble.tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '@/types/api';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[85%] rounded-lg p-4 ${
        isUser 
          ? 'bg-primary text-primary-foreground' 
          : 'bg-muted'
      }`}>
        {isUser ? (
          <p className="text-sm">{message.content}</p>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}
        
        {message.agentsUsed && message.agentsUsed.length > 0 && (
          <div className="mt-2 pt-2 border-t border-border/50 flex gap-1 flex-wrap">
            {message.agentsUsed.map((agent) => (
              <span key={agent} className="text-xs bg-background/50 px-2 py-0.5 rounded">
                {agent}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

---

## Step 2.10: Status Panel

```tsx
// frontend/src/components/status/StatusPanel.tsx
import { useStatusStore } from '@/stores/statusStore';
import { useChatStore } from '@/stores/chatStore';

export function StatusPanel() {
  const { agents, activeAgent, toolCalls, progress, currentTurn, maxTurns } = useStatusStore();
  const { isLoading } = useChatStore();
  
  return (
    <div className="h-full rounded-lg border border-border bg-card p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium">📋 Agent Status</span>
        {isLoading && (
          <span className="text-xs text-muted-foreground">
            Turn {currentTurn}/{maxTurns}
          </span>
        )}
      </div>
      
      {/* Progress Bar */}
      {isLoading && (
        <div className="mb-3">
          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
            <div 
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}
      
      {/* Agent Grid */}
      <div className="flex gap-2 flex-wrap">
        {Object.values(agents).map((agent) => (
          <div 
            key={agent.name}
            className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs transition-all ${
              agent.name === activeAgent
                ? 'bg-primary text-primary-foreground animate-pulse'
                : agent.status === 'completed'
                ? 'bg-green-500/20 text-green-500'
                : 'bg-muted text-muted-foreground'
            }`}
          >
            <span>{agent.emoji}</span>
            <span>{agent.name.replace('Crypto', '').replace('Agent', '')}</span>
          </div>
        ))}
      </div>
      
      {/* Latest Tool Call */}
      {toolCalls.length > 0 && (
        <div className="mt-2 text-xs text-muted-foreground truncate">
          ↳ {toolCalls[toolCalls.length - 1].tool_name}
        </div>
      )}
    </div>
  );
}
```

---

## Step 2.11: Chart Panel

```tsx
// frontend/src/components/charts/ChartPanel.tsx
import { useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi } from 'lightweight-charts';
import { useChartStore } from '@/stores/chartStore';
import { ChartControls } from './ChartControls';

export function ChartPanel() {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  
  const { symbol, interval, activeChart } = useChartStore();
  
  useEffect(() => {
    if (!chartContainerRef.current) return;
    
    // Create chart
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: 'solid', color: 'transparent' },
        textColor: '#9ca3af',
      },
      grid: {
        vertLines: { color: '#374151' },
        horzLines: { color: '#374151' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#374151',
      },
      timeScale: {
        borderColor: '#374151',
        timeVisible: true,
      },
    });
    
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderDownColor: '#ef4444',
      borderUpColor: '#22c55e',
      wickDownColor: '#ef4444',
      wickUpColor: '#22c55e',
    });
    
    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    
    // Load initial data (mock for now)
    const mockData = generateMockData();
    candleSeries.setData(mockData);
    chart.timeScale().fitContent();
    
    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };
    
    window.addEventListener('resize', handleResize);
    handleResize();
    
    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);
  
  return (
    <div className="h-full rounded-lg border border-border bg-card flex flex-col overflow-hidden">
      <ChartControls />
      
      <div className="flex-1 relative">
        <div ref={chartContainerRef} className="absolute inset-0" />
        
        {/* Symbol overlay */}
        <div className="absolute top-4 left-4 flex items-center gap-2 z-10">
          <span className="text-2xl font-bold text-foreground/80">{symbol}</span>
          <span className="text-sm text-muted-foreground">{interval}</span>
        </div>
      </div>
    </div>
  );
}

// Mock data generator
function generateMockData() {
  const data = [];
  let time = Math.floor(Date.now() / 1000) - 86400 * 30; // 30 days ago
  let price = 95000;
  
  for (let i = 0; i < 200; i++) {
    const open = price;
    const close = price * (1 + (Math.random() - 0.5) * 0.02);
    const high = Math.max(open, close) * (1 + Math.random() * 0.01);
    const low = Math.min(open, close) * (1 - Math.random() * 0.01);
    
    data.push({
      time: time as any,
      open,
      high,
      low,
      close,
    });
    
    price = close;
    time += 3600; // 1 hour
  }
  
  return data;
}
```

```tsx
// frontend/src/components/charts/ChartControls.tsx
import { useChartStore } from '@/stores/chartStore';
import { Button } from '../ui/button';

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'SUIUSDT', 'AVAXUSDT'];
const INTERVALS = ['15m', '1H', '4H', '1D', '1W'];
const INDICATORS = ['RSI', 'MACD', 'BB', 'SMA', 'EMA', 'Volume'];

export function ChartControls() {
  const { symbol, interval, indicators, setSymbol, setInterval, toggleIndicator } = useChartStore();
  
  return (
    <div className="px-4 py-3 border-b border-border flex items-center gap-4 flex-wrap">
      {/* Symbol Selector */}
      <div className="flex gap-1">
        {SYMBOLS.map((s) => (
          <Button
            key={s}
            variant={symbol === s ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setSymbol(s)}
          >
            {s.replace('USDT', '')}
          </Button>
        ))}
      </div>
      
      <div className="h-6 w-px bg-border" />
      
      {/* Interval Selector */}
      <div className="flex gap-1">
        {INTERVALS.map((i) => (
          <Button
            key={i}
            variant={interval === i ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setInterval(i)}
          >
            {i}
          </Button>
        ))}
      </div>
      
      <div className="h-6 w-px bg-border" />
      
      {/* Indicator Toggles */}
      <div className="flex gap-1">
        {INDICATORS.map((ind) => (
          <Button
            key={ind}
            variant={indicators.includes(ind.toLowerCase()) ? 'secondary' : 'ghost'}
            size="sm"
            onClick={() => toggleIndicator(ind.toLowerCase())}
          >
            {ind}
          </Button>
        ))}
      </div>
    </div>
  );
}
```

---

## Step 2.12: Settings Dialog

```tsx
// frontend/src/components/settings/SettingsDialog.tsx
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { ExchangeSettings } from './ExchangeSettings';
import { LLMSettings } from './LLMSettings';

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>⚙️ Settings</DialogTitle>
        </DialogHeader>
        
        <Tabs defaultValue="exchange">
          <TabsList className="w-full">
            <TabsTrigger value="exchange" className="flex-1">Exchange</TabsTrigger>
            <TabsTrigger value="llm" className="flex-1">LLM Provider</TabsTrigger>
          </TabsList>
          
          <TabsContent value="exchange" className="mt-4">
            <ExchangeSettings />
          </TabsContent>
          
          <TabsContent value="llm" className="mt-4">
            <LLMSettings />
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
```

```tsx
// frontend/src/components/settings/ExchangeSettings.tsx
import { useState } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Alert, AlertDescription } from '../ui/alert';
import { Lock, Check } from 'lucide-react';

export function ExchangeSettings() {
  const [credentials, setCredentials] = useState({
    apiKey: '',
    apiSecret: '',
    passphrase: '',
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  
  const handleSave = async () => {
    setSaving(true);
    try {
      const response = await fetch('/api/v1/settings/exchange', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials),
      });
      
      if (response.ok) {
        setSaved(true);
        setCredentials({ apiKey: '', apiSecret: '', passphrase: '' });
        setTimeout(() => setSaved(false), 3000);
      }
    } catch (error) {
      console.error('Failed to save credentials:', error);
    } finally {
      setSaving(false);
    }
  };
  
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-lg font-medium">
        <span>🔶</span>
        <span>Bitget Exchange</span>
      </div>
      
      <div className="space-y-3">
        <div>
          <Label htmlFor="apiKey">API Key</Label>
          <Input
            id="apiKey"
            type="password"
            value={credentials.apiKey}
            onChange={(e) => setCredentials({ ...credentials, apiKey: e.target.value })}
            placeholder="Enter your Bitget API key"
          />
        </div>
        
        <div>
          <Label htmlFor="apiSecret">API Secret</Label>
          <Input
            id="apiSecret"
            type="password"
            value={credentials.apiSecret}
            onChange={(e) => setCredentials({ ...credentials, apiSecret: e.target.value })}
            placeholder="Enter your API secret"
          />
        </div>
        
        <div>
          <Label htmlFor="passphrase">Passphrase</Label>
          <Input
            id="passphrase"
            type="password"
            value={credentials.passphrase}
            onChange={(e) => setCredentials({ ...credentials, passphrase: e.target.value })}
            placeholder="Enter your passphrase"
          />
        </div>
      </div>
      
      <Alert>
        <Lock className="h-4 w-4" />
        <AlertDescription>
          Credentials are encrypted with AES-256 and stored securely in the container.
          They are never transmitted in plain text after saving.
        </AlertDescription>
      </Alert>
      
      <Button 
        onClick={handleSave} 
        disabled={saving || !credentials.apiKey}
        className="w-full"
      >
        {saved ? (
          <>
            <Check className="mr-2 h-4 w-4" />
            Saved Successfully
          </>
        ) : (
          saving ? 'Saving...' : 'Save Credentials'
        )}
      </Button>
    </div>
  );
}
```

---

## Step 2.13: App Entry Point

```tsx
// frontend/src/App.tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MainLayout } from './components/layout/MainLayout';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="dark">
        <MainLayout />
      </div>
    </QueryClientProvider>
  );
}

export default App;
```

```tsx
// frontend/src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

```css
/* frontend/src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 222.2 84% 4.9%;
    --radius: 0.5rem;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --primary: 210 40% 98%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 212.7 26.8% 83.9%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  }
}
```

---

## Next Steps

After completing Phase 2, proceed to:
- [Phase 3: Real-time Communication](./PHASE_3_REALTIME.md)

---

*Document created: 2025-11-29*
