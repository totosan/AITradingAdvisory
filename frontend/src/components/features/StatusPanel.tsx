import { PanelContainer } from "@/components/layout";
import { Badge, Spinner } from "@/components/ui";
import { useStatusStore } from "@/stores/statusStore";

const AGENT_EMOJIS: Record<string, string> = {
  CryptoMarketAnalyst: "📊",
  TechnicalAnalyst: "📈",
  ChartingAgent: "📉",
  CryptoAnalysisCoder: "💻",
  ReportWriter: "📝",
  Executor: "⚙️",
  Orchestrator: "🎯",
};

export function StatusPanel() {
  const { agents, isConnected, activeAgent, toolCalls } = useStatusStore();

  return (
    <PanelContainer title="🎯 Agent Status" className="h-full">
      <div className="space-y-4">
        {/* Connection Status */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Connection</span>
          <Badge variant={isConnected ? "success" : "destructive"}>
            {isConnected ? "Connected" : "Disconnected"}
          </Badge>
        </div>

        {/* Current Agent */}
        {activeAgent && (
          <div className="flex items-center gap-2 p-2 rounded-lg bg-secondary/50">
            <Spinner size="sm" />
            <span className="text-sm">
              {AGENT_EMOJIS[activeAgent] || "🤖"} {activeAgent}
            </span>
          </div>
        )}

        {/* Agent List */}
        <div className="space-y-2">
          <div className="text-xs text-muted-foreground uppercase tracking-wide">
            Agents
          </div>
          <div className="grid grid-cols-2 gap-2">
            {agents.map((agent) => (
              <div
                key={agent.name}
                className={`flex items-center gap-2 p-2 rounded-lg text-sm ${
                  agent.status === "working"
                    ? "bg-yellow-500/10 border border-yellow-500/30"
                    : agent.status === "completed"
                    ? "bg-green-500/10 border border-green-500/30"
                    : agent.status === "error"
                    ? "bg-red-500/10 border border-red-500/30"
                    : "bg-secondary/30"
                }`}
              >
                <span>{AGENT_EMOJIS[agent.name] || "🤖"}</span>
                <span className="truncate">{agent.name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Tool Calls */}
        {toolCalls.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs text-muted-foreground uppercase tracking-wide">
              Recent Tools
            </div>
            <div className="space-y-1 max-h-24 overflow-y-auto">
              {toolCalls.slice(-5).map((tool, idx) => (
                <div
                  key={idx}
                  className="text-xs p-2 rounded bg-secondary/30 font-mono truncate"
                >
                  {tool.tool_name}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </PanelContainer>
  );
}
