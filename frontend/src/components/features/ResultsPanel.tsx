import { PanelContainer } from "@/components/layout";
import { ScrollArea } from "@/components/ui";
import { useChatStore } from "@/stores/chatStore";
import ReactMarkdown from "react-markdown";

export function ResultsPanel() {
  const { messages, finalResult } = useChatStore();

  // Get the most recent assistant message as the result
  const latestResult = finalResult || messages
    .filter((m) => m.role === "assistant")
    .slice(-1)[0]?.content;

  return (
    <PanelContainer title="📋 Results" className="h-full">
      <ScrollArea className="h-full">
        {latestResult ? (
          <div className="markdown-content prose prose-invert prose-sm max-w-none">
            <ReactMarkdown>{latestResult}</ReactMarkdown>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground py-8">
            <span className="text-4xl mb-4">📋</span>
            <p className="text-sm">Analysis results will appear here</p>
            <p className="text-xs mt-2">
              Start a conversation to see crypto insights
            </p>
          </div>
        )}
      </ScrollArea>
    </PanelContainer>
  );
}
