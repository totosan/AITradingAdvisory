import { useState } from "react";
import { Spinner } from "@/components/ui";
import { useStatusStore } from "@/stores/statusStore";

const AGENT_EMOJIS: Record<string, string> = {
  CryptoMarketAnalyst: "📊",
  TechnicalAnalyst: "📈",
  ChartingAgent: "📉",
  CryptoAnalysisCoder: "💻",
  ReportWriter: "📝",
  Executor: "⚙️",
  Orchestrator: "🎯",
  MagenticOneOrchestrator: "🎯",
};

type AgentStatus = "idle" | "working" | "completed" | "error";

function getStatusColor(status: AgentStatus): string {
  switch (status) {
    case "working":
      return "bg-yellow-400";
    case "completed":
      return "bg-emerald-400";
    case "error":
      return "bg-red-400";
    default:
      return "bg-slate-500";
  }
}

function getStatusRing(status: AgentStatus): string {
  switch (status) {
    case "working":
      return "ring-yellow-400/50";
    case "completed":
      return "ring-emerald-400/50";
    case "error":
      return "ring-red-400/50";
    default:
      return "ring-transparent";
  }
}

export function StatusPanel() {
  const { agents, isConnected, activeAgent, toolCalls } = useStatusStore();
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="h-full flex flex-col">
      {/* Compact header bar - always visible */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-3 px-3 py-2 bg-slate-900/80 backdrop-blur-sm border border-slate-700/50 rounded-lg cursor-pointer hover:bg-slate-800/80 transition-colors group"
      >
        {/* Connection indicator */}
        <div className="flex items-center gap-1.5">
          <div
            className={`w-2 h-2 rounded-full transition-colors ${
              isConnected ? "bg-emerald-400 shadow-emerald-400/50 shadow-sm" : "bg-red-400"
            }`}
          />
          <span className="text-[10px] text-slate-400 uppercase tracking-wider">
            {isConnected ? "Live" : "Off"}
          </span>
        </div>

        <div className="w-px h-4 bg-slate-700" />

        {/* Active agent indicator */}
        {activeAgent ? (
          <div className="flex items-center gap-1.5 text-xs text-slate-300">
            <Spinner size="sm" className="w-3 h-3" />
            <span className="opacity-70">{AGENT_EMOJIS[activeAgent] || "🤖"}</span>
            <span className="text-[10px] text-slate-400 max-w-[100px] truncate">
              {activeAgent}
            </span>
          </div>
        ) : (
          <span className="text-[10px] text-slate-500">Idle</span>
        )}

        <div className="w-px h-4 bg-slate-700" />

        {/* Agent dots - compact visual */}
        <div className="flex items-center gap-1">
          {agents.map((agent) => (
            <div
              key={agent.name}
              title={`${agent.name}: ${agent.status}`}
              className={`w-2.5 h-2.5 rounded-full transition-all ring-2 ${getStatusColor(
                agent.status as AgentStatus
              )} ${getStatusRing(agent.status as AgentStatus)} ${
                agent.status === "working" ? "animate-pulse" : ""
              }`}
            />
          ))}
        </div>

        {/* Expand indicator */}
        <div className="ml-auto flex items-center gap-1">
          {toolCalls.length > 0 && (
            <span className="text-[10px] text-slate-500">
              {toolCalls.length} calls
            </span>
          )}
          <svg
            className={`w-3 h-3 text-slate-500 transition-transform duration-200 ${
              isExpanded ? "rotate-180" : ""
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </div>
      </div>

      {/* Expandable details */}
      <div
        className={`overflow-hidden transition-all duration-300 ease-in-out ${
          isExpanded ? "flex-1 opacity-100 mt-2" : "max-h-0 opacity-0"
        }`}
      >
        <div className="h-full bg-slate-900/60 backdrop-blur-sm border border-slate-700/50 rounded-lg p-3 space-y-3 overflow-y-auto">
          {/* Agent grid - compact */}
          <div className="grid grid-cols-3 gap-1.5">
            {agents.map((agent) => (
              <div
                key={agent.name}
                className={`flex items-center gap-1.5 px-2 py-1.5 rounded text-[11px] transition-all ${
                  agent.status === "working"
                    ? "bg-yellow-500/10 border border-yellow-500/20"
                    : agent.status === "completed"
                    ? "bg-emerald-500/10 border border-emerald-500/20"
                    : agent.status === "error"
                    ? "bg-red-500/10 border border-red-500/20"
                    : "bg-slate-800/50 border border-slate-700/30"
                }`}
              >
                <span className="text-xs">{AGENT_EMOJIS[agent.name] || "🤖"}</span>
                <span className="truncate text-slate-300">{agent.name}</span>
              </div>
            ))}
          </div>

          {/* Recent tool calls - minimal */}
          {toolCalls.length > 0 && (
            <div className="space-y-1">
              <div className="text-[10px] text-slate-500 uppercase tracking-wider">
                Recent Tools
              </div>
              <div className="flex flex-wrap gap-1">
                {toolCalls.slice(-5).map((tool, idx) => (
                  <span
                    key={idx}
                    className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800/70 text-slate-400 font-mono"
                  >
                    {tool.tool_name}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
