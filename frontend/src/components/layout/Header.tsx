import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { SettingsDialog } from "@/components/settings";

interface HeaderProps {
  className?: string;
}

export function Header({ className }: HeaderProps) {
  const [settingsOpen, setSettingsOpen] = React.useState(false);
  
  return (
    <>
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
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSettingsOpen(true)}
            title="Settings"
          >
            <span className="text-lg">⚙️</span>
          </Button>
        </div>
      </header>
      
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </>
  );
}
