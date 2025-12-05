import { cn } from "@/lib/utils";
import type { Message } from "@/types/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Paperclip, Bot, User, ChevronDown, ChevronUp, Shield, Copy, Check, RefreshCw } from "lucide-react";
import { useState } from "react";

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
  const isContentFilterError = message.role === "content_filter_error";
  const isAgent = message.role === "agent";
  const isSystem = message.role === "system";

  // For content filter errors, use dedicated component
  if (isContentFilterError && message.contentFilterDetails) {
    return (
      <ContentFilterErrorBubble 
        message={message} 
        isLatest={isLatest} 
      />
    );
  }

  // For retry notifications, use dedicated component
  if (isSystem && message.isRetryNotification) {
    return (
      <RetryNotificationBubble
        message={message}
        isLatest={isLatest}
      />
    );
  }

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

/**
 * Special error bubble for Content Filter errors with expandable prompt view.
 * Follows UX best practices:
 * - Clear error identification with distinct styling
 * - Collapsible details to avoid overwhelming users
 * - Copy button for easy debugging/sharing
 * - Filter type badge for quick identification
 */
function ContentFilterErrorBubble({ message, isLatest }: MessageBubbleProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  
  const details = message.contentFilterDetails!;
  const filterType = details.filter_type || "unknown";
  
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(details.triggered_prompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };
  
  // Map filter types to user-friendly labels
  const filterTypeLabels: Record<string, string> = {
    jailbreak: "Jailbreak Detection",
    hate: "Hate Speech",
    violence: "Violence",
    sexual: "Sexual Content",
    self_harm: "Self-Harm",
    unknown: "Content Policy",
  };
  
  return (
    <div 
      className={cn(
        "flex gap-3 justify-start",
        isLatest && "animate-slide-up"
      )}
    >
      {/* Shield icon for content filter */}
      <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center border border-amber-500/30">
        <Shield className="w-4 h-4" />
      </div>
      
      <div className="max-w-[85%] rounded-2xl overflow-hidden border border-amber-500/30 bg-amber-950/30">
        {/* Header section */}
        <div className="px-4 py-3 border-b border-amber-500/20 bg-amber-950/50">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="text-amber-400 font-medium text-sm">
                ⚠️ Content Filter Triggered
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wider bg-amber-500/20 text-amber-300 border border-amber-500/30">
                {filterTypeLabels[filterType] || filterType}
              </span>
            </div>
          </div>
          <p className="text-xs text-amber-200/70 mt-1.5">
            Azure OpenAI's content filter was triggered by the prompt sent to the AI.
          </p>
        </div>
        
        {/* Main message */}
        <div className="px-4 py-3">
          <p className="text-sm text-foreground/80">
            {message.content}
          </p>
          
          {/* Expandable prompt section */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="mt-3 w-full flex items-center justify-between px-3 py-2 rounded-lg bg-slate-800/50 hover:bg-slate-800/70 transition-colors border border-white/[0.06] group"
          >
            <span className="text-xs font-medium text-foreground/70 group-hover:text-foreground/90 transition-colors">
              {isExpanded ? "Hide" : "Show"} Triggered Prompt
            </span>
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            )}
          </button>
          
          {/* Expanded prompt content */}
          {isExpanded && (
            <div className="mt-2 rounded-lg bg-slate-900/80 border border-white/[0.08] overflow-hidden">
              {/* Prompt header with copy button */}
              <div className="flex items-center justify-between px-3 py-2 border-b border-white/[0.06] bg-slate-800/30">
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium">
                  Prompt that triggered the filter
                </span>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-medium text-muted-foreground hover:text-foreground hover:bg-white/[0.05] transition-colors"
                >
                  {copied ? (
                    <>
                      <Check className="w-3 h-3 text-emerald-400" />
                      <span className="text-emerald-400">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" />
                      Copy
                    </>
                  )}
                </button>
              </div>
              
              {/* Prompt content */}
              <pre className="px-3 py-3 text-xs text-foreground/70 whitespace-pre-wrap break-words max-h-[300px] overflow-y-auto font-mono leading-relaxed">
                {details.triggered_prompt}
              </pre>
              
              {/* Filter results (if available) */}
              {details.filter_results && Object.keys(details.filter_results).length > 0 && (
                <div className="px-3 py-2 border-t border-white/[0.06] bg-slate-800/20">
                  <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-medium block mb-2">
                    Filter Details
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(details.filter_results).map(([key, value]) => {
                      const result = value as { filtered?: boolean; detected?: boolean; severity?: string };
                      const isTriggered = result?.filtered || result?.detected;
                      return (
                        <span
                          key={key}
                          className={cn(
                            "px-2 py-1 rounded text-[10px] font-medium",
                            isTriggered 
                              ? "bg-red-500/20 text-red-300 border border-red-500/30"
                              : "bg-slate-700/50 text-slate-400 border border-slate-600/30"
                          )}
                        >
                          {key}: {result?.severity || (isTriggered ? "triggered" : "safe")}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}
          
          {/* Help text */}
          <p className="mt-3 text-[11px] text-muted-foreground/60">
            💡 Tip: Try rephrasing your request using neutral, professional language.
            Avoid terms that might be interpreted as harmful or manipulative.
          </p>
        </div>
        
        {/* Timestamp */}
        <div className="px-4 pb-2">
          <span className="text-[10px] text-muted-foreground/50">
            {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>
      </div>
    </div>
  );
}

/**
 * Retry notification bubble - shown when the system is automatically retrying
 * after a content filter error with a sanitized prompt.
 * Uses a subtle, non-alarming design to indicate ongoing processing.
 */
function RetryNotificationBubble({ message, isLatest }: MessageBubbleProps) {
  const retryInfo = message.retryInfo;
  
  return (
    <div 
      className={cn(
        "flex gap-3 justify-center",
        isLatest && "animate-slide-up"
      )}
    >
      <div className="flex items-center gap-3 px-4 py-2.5 rounded-full bg-blue-950/40 border border-blue-500/20">
        {/* Spinning refresh icon */}
        <RefreshCw className="w-4 h-4 text-blue-400 animate-spin" />
        
        {/* Message content */}
        <div className="flex flex-col gap-0.5">
          <span className="text-sm text-blue-200/90 font-medium">
            {message.content.replace('⏳ ', '')}
          </span>
          {retryInfo && (
            <span className="text-[10px] text-blue-300/60">
              Versuch {retryInfo.retry_count + 1} von {retryInfo.max_retries + 1}
              {retryInfo.filter_type && ` • Filter: ${retryInfo.filter_type}`}
            </span>
          )}
        </div>
        
        {/* Progress dots */}
        <div className="flex gap-1">
          {retryInfo && Array.from({ length: retryInfo.max_retries }).map((_, i) => (
            <div
              key={i}
              className={cn(
                "w-1.5 h-1.5 rounded-full transition-colors",
                i < retryInfo.retry_count
                  ? "bg-blue-400"
                  : "bg-blue-400/30"
              )}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
