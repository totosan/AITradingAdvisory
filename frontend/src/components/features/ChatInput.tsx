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

  return (
    <div className="relative">
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={!isConnected || isProcessing}
        className="pr-12 min-h-[44px] max-h-[150px]"
        rows={1}
      />
      <button
        onClick={handleSubmit}
        disabled={!value.trim() || !isConnected || isProcessing}
        className="absolute right-2 bottom-2 p-2 rounded-md bg-primary text-primary-foreground disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors"
      >
        <Send className="h-4 w-4" />
      </button>
    </div>
  );
}
