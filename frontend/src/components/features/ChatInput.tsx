import { useRef, useEffect } from "react";
import { Textarea } from "@/components/ui";
import { Send } from "lucide-react";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (message: string) => void;
  isProcessing: boolean;
  isConnected: boolean;
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  isProcessing,
  isConnected,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        150
      )}px`;
    }
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit(value);
    }
  };

  const handleSubmit = () => {
    onSubmit(value);
  };

  const placeholder = !isConnected
    ? "Connecting..."
    : isProcessing
    ? "Waiting for response..."
    : "Ask about crypto markets... (e.g., 'Analyze Bitcoin price')";

  const canSubmit = value.trim() && isConnected && !isProcessing;

  return (
    <div className="relative group">
      {/* Glow effect on focus */}
      <div className="absolute -inset-0.5 bg-gradient-to-r from-emerald-500/20 to-cyan-500/20 rounded-xl blur opacity-0 group-focus-within:opacity-100 transition-opacity duration-300" />
      
      <div className="relative flex items-end gap-2 p-1 rounded-xl bg-slate-800/50 border border-white/[0.08] backdrop-blur-sm group-focus-within:border-emerald-500/30 transition-colors">
        <Textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={!isConnected || isProcessing}
          className="flex-1 min-h-[44px] max-h-[150px] px-3 py-3 bg-transparent border-0 resize-none focus:ring-0 focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-muted-foreground/50"
          rows={1}
        />
        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className={`
            flex-shrink-0 p-2.5 m-1 rounded-lg transition-all duration-200
            ${canSubmit 
              ? 'bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-900 shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40 hover:scale-105 active:scale-95' 
              : 'bg-slate-700/50 text-slate-500 cursor-not-allowed'
            }
          `}
        >
          <Send className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
