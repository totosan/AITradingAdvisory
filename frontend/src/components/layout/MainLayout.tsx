import { Header } from "./Header";
import { ChatPanel } from "@/components/features/ChatPanel";
import { StatusPanel } from "@/components/features/StatusPanel";
import { ResultsPanel } from "@/components/features/ResultsPanel";
import { ChartPanel } from "@/components/features/ChartPanel";

export function MainLayout() {
  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      <Header />
      
      {/* Main content area - 4 panel grid */}
      <main className="flex-1 p-4 overflow-hidden">
        <div className="h-full grid grid-cols-12 grid-rows-6 gap-4">
          {/* Left column: Chat (rows 1-4) + Status (rows 5-6) */}
          <div className="col-span-4 row-span-4">
            <ChatPanel />
          </div>
          <div className="col-span-4 row-span-2">
            <StatusPanel />
          </div>
          
          {/* Right column: Results (rows 1-3) + Charts (rows 4-6) */}
          <div className="col-span-8 row-span-3">
            <ResultsPanel />
          </div>
          <div className="col-span-8 row-span-3">
            <ChartPanel />
          </div>
        </div>
      </main>
    </div>
  );
}
