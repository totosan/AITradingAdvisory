import { cn } from "@/lib/utils";
import type { Message } from "@/types/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Paperclip, Bot, User } from "lucide-react";

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center py-12">
        <div className="relative mb-6">
          <span className="text-5xl animate-float">🔮</span>
          <div className="absolute inset-0 bg-purple-500/20 blur-2xl -z-10" />
        </div>
        <p className="text-sm text-foreground/80 font-medium">Ask me about cryptocurrency markets</p>
        <p className="text-xs text-muted-foreground/60 mt-2">
          Try: "Analyze Bitcoin price" or "Compare ETH and SOL"
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {messages.map((message, index) => (
        <MessageBubble 
          key={message.id} 
          message={message} 
          isLatest={index === messages.length - 1}
        />
      ))}
    </div>
  );
}

interface MessageBubbleProps {
  message: Message;
  isLatest?: boolean;
}

function MessageBubble({ message, isLatest }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const isError = message.role === "error";
  const isAgent = message.role === "agent";

  return (
    <div 
      className={cn(
        "flex gap-3",
        isUser ? "justify-end" : "justify-start",
        isLatest && "animate-slide-up"
      )}
    >
      {/* Avatar for assistant/agent messages */}
      {!isUser && (
        <div className={cn(
          "flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-sm",
          isError 
            ? "bg-red-500/20 text-red-400" 
            : "bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 text-emerald-400 border border-emerald-500/20"
        )}>
          {isError ? "⚠️" : <Bot className="w-4 h-4" />}
        </div>
      )}
      
      <div
        className={cn(
          "max-w-[80%] px-4 py-3",
          isUser && "message-user",
          !isUser && !isError && "message-assistant",
          isError && "message-error"
        )}
      >
        {(message.agentName || isAgent) && (
          <div className="flex items-center gap-1.5 text-[11px] text-emerald-400/80 mb-1.5 font-medium uppercase tracking-wider">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400/60" />
            {message.agentName || "Agent"}
          </div>
        )}
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
        ) : (
          <div className="markdown-content text-sm">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                // Custom code block rendering
                code({ className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || "");
                  const isInline = !match && !className;
                  return isInline ? (
                    <code className={className} {...props}>
                      {children}
                    </code>
                  ) : (
                    <code className={`${className} block`} {...props}>
                      {children}
                    </code>
                  );
                },
                // Make links open in new tab
                a({ href, children, ...props }) {
                  return (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-emerald-400 hover:text-emerald-300 underline underline-offset-2 transition-colors"
                      {...props}
                    >
                      {children}
                    </a>
                  );
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
        {message.attachments?.length ? (
          <div className="mt-3 rounded-lg overflow-hidden border border-white/[0.08] bg-slate-800/30">
            {message.attachments.map((attachment) => (
              <a
                key={attachment.id}
                href={attachment.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2.5 px-3 py-2.5 text-xs hover:bg-white/[0.05] transition-colors group"
              >
                <div className="p-1.5 rounded bg-emerald-500/10 text-emerald-400 group-hover:bg-emerald-500/20 transition-colors">
                  <Paperclip className="h-3.5 w-3.5" />
                </div>
                <span className="font-medium text-foreground/90">{attachment.label}</span>
                <span className="text-emerald-400/60 text-[10px] uppercase tracking-wider ml-auto">View →</span>
              </a>
            ))}
          </div>
        ) : null}
        <div className="text-[10px] text-muted-foreground/50 mt-2">
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </div>
      </div>
      
      {/* Avatar for user messages */}
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center text-slate-900">
          <User className="w-4 h-4" />
        </div>
      )}
    </div>
  );
}
