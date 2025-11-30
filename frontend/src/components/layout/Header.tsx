import { cn } from "@/lib/utils";

interface HeaderProps {
  className?: string;
}

export function Header({ className }: HeaderProps) {
  return (
    <header className={cn("h-14 border-b border-border bg-card px-6 flex items-center justify-between", className)}>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">🔮</span>
          <h1 className="text-lg font-semibold text-foreground">MagenticOne</h1>
        </div>
        <span className="text-sm text-muted-foreground">Crypto Analysis Platform</span>
      </div>
      
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm">
          <span className="text-muted-foreground">Connected to:</span>
          <span className="text-green-500 flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            Ollama
          </span>
        </div>
      </div>
    </header>
  );
}
