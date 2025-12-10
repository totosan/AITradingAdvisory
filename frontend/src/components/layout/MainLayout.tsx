import { useState } from "react";
import { Header } from "./Header";
import { ChatPanel } from "@/components/features/ChatPanel";
import { StatusPanel } from "@/components/features/StatusPanel";
import { ChartPanel } from "@/components/features/ChartPanel";
import { PredictionsPanel } from "@/components/features/PredictionsPanel";
import { PerformanceDashboard } from "@/components/features/PerformanceDashboard";

type RightPanelTab = "charts" | "predictions" | "performance";

export function MainLayout() {
  const [rightPanelTab, setRightPanelTab] = useState<RightPanelTab>("charts");

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      <Header />
      
      {/* Main content area - 4 panel grid */}
      <main className="flex-1 p-4 overflow-hidden">
        <div className="h-full min-h-0 grid grid-cols-12 gap-4">
          {/* Left column: Chat wider with agent panel below */}
          <div className="col-span-5 h-full flex flex-col gap-2 min-h-0">
            <div className="flex-1 min-h-0">
              <ChatPanel />
            </div>
            <div className="flex-shrink-0">
              <StatusPanel />
            </div>
          </div>

          {/* Right column: Tabbed content */}
          <div className="col-span-7 h-full min-h-0 flex flex-col">
            {/* Tab Bar */}
            <div className="flex gap-1 mb-2 bg-gray-800 p-1 rounded-lg">
              <TabButton
                active={rightPanelTab === "charts"}
                onClick={() => setRightPanelTab("charts")}
              >
                📊 Charts
              </TabButton>
              <TabButton
                active={rightPanelTab === "predictions"}
                onClick={() => setRightPanelTab("predictions")}
              >
                🎯 Predictions
              </TabButton>
              <TabButton
                active={rightPanelTab === "performance"}
                onClick={() => setRightPanelTab("performance")}
              >
                📈 Performance
              </TabButton>
            </div>

            {/* Tab Content */}
            <div className="flex-1 min-h-0">
              {rightPanelTab === "charts" && <ChartPanel />}
              {rightPanelTab === "predictions" && <PredictionsPanel />}
              {rightPanelTab === "performance" && <PerformanceDashboard />}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

// Tab button component
function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium rounded transition-colors ${
        active
          ? "bg-blue-600 text-white"
          : "text-gray-400 hover:text-white hover:bg-gray-700"
      }`}
    >
      {children}
    </button>
  );
}
