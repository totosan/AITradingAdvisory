import { useState, useRef, useEffect } from "react";
import { PanelContainer } from "@/components/layout";
import { ScrollArea, Button, Spinner } from "@/components/ui";
import { ChatInput } from "./ChatInput";
import { MessageList } from "./MessageList";
import { useChatStore } from "@/stores/chatStore";
import { useStatusStore } from "@/stores/statusStore";
import { useWebSocket } from "@/hooks";

export function ChatPanel() {
  const {
    messages,
    isProcessing,
    setIsProcessing,
    clearMessages,
    startNewConversation,
  } = useChatStore();
  const { isConnected } = useStatusStore();
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
    setIsProcessing(false);
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
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              clearMessages();
              handleNewConversation();
            }}
            disabled={isProcessing}
          >
            New Chat
          </Button>
          <span
            className={`w-2 h-2 rounded-full ${
              isConnected ? "bg-green-500" : "bg-red-500"
            }`}
          />
          <span className="text-xs text-muted-foreground">
            {isConnected ? "Connected" : "Disconnected"}
          </span>
        </div>
      }
    >
      <div className="flex flex-col h-full">
        <ScrollArea ref={scrollRef} className="flex-1 pr-2">
          <MessageList messages={messages} />
          {isProcessing && (
            <div className="flex items-center gap-2 text-muted-foreground text-sm py-2">
              <Spinner size="sm" />
              <span>Agents are working...</span>
            </div>
          )}
        </ScrollArea>

        <div className="pt-4 border-t border-border mt-2">
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
              className="mt-2 w-full"
            >
              Cancel
            </Button>
          )}
        </div>
      </div>
    </PanelContainer>
  );
}
