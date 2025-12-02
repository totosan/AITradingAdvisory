import { Header } from "./Header";
import { ChatPanel } from "@/components/features/ChatPanel";
import { StatusPanel } from "@/components/features/StatusPanel";
import { ChartPanel } from "@/components/features/ChartPanel";

export function MainLayout() {
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

          {/* Right column: Charts anchored to the top */}
          <div className="col-span-7 h-full min-h-0">
            <ChartPanel />
          </div>
        </div>
      </main>
    </div>
  );
}
