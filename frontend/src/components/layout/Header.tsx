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
      <header 
        className={cn(
          "h-16 px-6 flex items-center justify-between relative z-10",
          "border-b border-white/[0.06]",
          "bg-gradient-to-r from-slate-900/80 via-slate-900/60 to-slate-900/80",
          "backdrop-blur-xl",
          className
        )}
      >
        {/* Subtle top highlight */}
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
        
        <div className="flex items-center gap-4">
          {/* Logo with glow effect */}
          <div className="flex items-center gap-3 group">
            <div className="relative">
              <span className="text-2xl relative z-10 group-hover:scale-110 transition-transform duration-300">🔮</span>
              <div className="absolute inset-0 bg-purple-500/30 blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
            </div>
            <div className="flex flex-col">
              <h1 className="text-base font-bold bg-gradient-to-r from-white to-white/70 bg-clip-text text-transparent tracking-tight">
                MagenticOne
              </h1>
              <span className="text-[10px] text-muted-foreground/70 uppercase tracking-widest font-medium">
                Crypto Analysis
              </span>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-6">
          {/* Connection status with modern indicator */}
          <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-white/[0.03] border border-white/[0.06]">
            <span className="text-xs text-muted-foreground">Connected to:</span>
            <div className="flex items-center gap-1.5">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400 shadow-lg shadow-emerald-400/50"></span>
              </span>
              <span className="text-xs font-medium text-emerald-400">Ollama</span>
            </div>
          </div>
          
          {/* Settings button with hover effect */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSettingsOpen(true)}
            className="relative group hover:bg-white/[0.06] rounded-lg transition-all duration-200"
            title="Settings"
          >
            <span className="text-lg group-hover:rotate-45 transition-transform duration-300">⚙️</span>
          </Button>
        </div>
      </header>
      
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
    </>
  );
}
