import { useState, useRef, useEffect } from "react";
import { PanelContainer } from "@/components/layout";
import { ScrollArea, Button, Spinner } from "@/components/ui";
import { ChatInput } from "./ChatInput";
import { MessageList } from "./MessageList";
import { useChatStore } from "@/stores/chatStore";
import { useStatusStore } from "@/stores/statusStore";
import { useWebSocket } from "@/hooks";
import { Plus, X } from "lucide-react";

export function ChatPanel() {
  const {
    messages,
    clearMessages,
    startNewConversation,
  } = useChatStore();
  const { isConnected, isProcessing } = useStatusStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [inputValue, setInputValue] = useState("");

  const { sendMessage, cancelProcessing } = useWebSocket();

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = (message: string) => {
    if (!message.trim() || isProcessing) return;
    sendMessage(message);
    setInputValue("");
  };

  const handleCancel = () => {
    cancelProcessing();
  };

  const handleNewConversation = () => {
    const newId = startNewConversation();
    console.log("Started conversation", newId);
  };

  return (
    <PanelContainer
      title="💬 Chat"
      className="h-full"
      headerActions={
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              clearMessages();
              handleNewConversation();
            }}
            disabled={isProcessing}
            className="h-7 px-2.5 text-xs gap-1.5 hover:bg-white/[0.08]"
          >
            <Plus className="w-3.5 h-3.5" />
            New Chat
          </Button>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-white/[0.03] border border-white/[0.06]">
            <span className="relative flex h-2 w-2">
              {isConnected && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              )}
              <span className={`relative inline-flex rounded-full h-2 w-2 ${
                isConnected ? "bg-emerald-400 shadow-lg shadow-emerald-400/50" : "bg-red-400 shadow-lg shadow-red-400/50"
              }`}></span>
            </span>
            <span className="text-[10px] text-muted-foreground">
              {isConnected ? "Connected" : "Offline"}
            </span>
          </div>
        </div>
      }
    >
      <div className="flex flex-col h-full">
        <ScrollArea ref={scrollRef} className="flex-1 pr-2">
          <MessageList messages={messages} />
          {isProcessing && (
            <div className="flex items-center gap-2.5 px-4 py-3 mt-2 rounded-xl bg-slate-800/30 border border-white/[0.06] animate-slide-up">
              <div className="relative">
                <Spinner size="sm" className="text-emerald-400" />
                <div className="absolute inset-0 bg-emerald-400/20 blur-md" />
              </div>
              <span className="text-sm text-foreground/70">Agents are working...</span>
            </div>
          )}
        </ScrollArea>

        <div className="pt-4 mt-2">
          <ChatInput
            value={inputValue}
            onChange={setInputValue}
            onSubmit={handleSubmit}
            isProcessing={isProcessing}
            isConnected={isConnected}
          />
          {isProcessing && (
            <Button
              variant="destructive"
              size="sm"
              onClick={handleCancel}
              className="mt-3 w-full gap-1.5"
            >
              <X className="w-3.5 h-3.5" />
              Cancel
            </Button>
          )}
        </div>
      </div>
    </PanelContainer>
  );
}
