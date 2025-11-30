import { cn } from "@/lib/utils";
import type { Message } from "@/types/api";
import ReactMarkdown from "react-markdown";

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground py-8">
        <span className="text-4xl mb-4">🔮</span>
        <p className="text-sm">Ask me about cryptocurrency markets</p>
        <p className="text-xs mt-2">
          Try: "Analyze Bitcoin price" or "Compare ETH and SOL"
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
    </div>
  );
}

interface MessageBubbleProps {
  message: Message;
}

function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isError = message.role === "error";
  const isAgent = message.role === "agent";

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] px-4 py-2",
          isUser && "message-user",
          !isUser && !isError && "message-assistant",
          isError && "message-error"
        )}
      >
        {(message.agentName || isAgent) && (
          <div className="text-xs text-muted-foreground mb-1 font-medium">
            {message.agentName || "Agent"}
          </div>
        )}
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="markdown-content text-sm">
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
        <div className="text-xs text-muted-foreground mt-1 opacity-70">
          {new Date(message.timestamp).toLocaleTimeString()}
        </div>
      </div>
    </div>
  );
}
