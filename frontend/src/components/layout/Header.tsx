import * as React from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { SettingsDialog } from "@/components/settings";
import { useAuthStore } from "@/stores/authStore";
import { settingsClient } from "@/services/settings";

interface HeaderProps {
  className?: string;
}

export function Header({ className }: HeaderProps) {
  const [settingsOpen, setSettingsOpen] = React.useState(false);
  const [llmProvider, setLlmProvider] = React.useState<string | null>(null);
  const { user, logout, token } = useAuthStore();
  
  // Fetch LLM provider on mount and when settings change
  React.useEffect(() => {
    if (!token) return;
    
    const fetchProvider = async () => {
      try {
        const status = await settingsClient.getLLMStatus();
        setLlmProvider(status.provider || 'Unknown');
      } catch {
        setLlmProvider(null);
      }
    };
    
    fetchProvider();
  }, [token, settingsOpen]); // Refetch when settings dialog closes
  
  // Format provider name for display
  const providerDisplay = React.useMemo(() => {
    if (!llmProvider) return 'Connecting...';
    const names: Record<string, string> = {
      'azure': 'Azure OpenAI',
      'ollama': 'Ollama',
      'openai': 'OpenAI',
    };
    return names[llmProvider.toLowerCase()] || llmProvider;
  }, [llmProvider]);
  
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
                AI-TradingAdvisory
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
                <span className={cn(
                  "animate-ping absolute inline-flex h-full w-full rounded-full opacity-75",
                  llmProvider ? "bg-emerald-400" : "bg-yellow-400"
                )}></span>
                <span className={cn(
                  "relative inline-flex rounded-full h-2 w-2 shadow-lg",
                  llmProvider ? "bg-emerald-400 shadow-emerald-400/50" : "bg-yellow-400 shadow-yellow-400/50"
                )}></span>
              </span>
              <span className={cn(
                "text-xs font-medium",
                llmProvider ? "text-emerald-400" : "text-yellow-400"
              )}>{providerDisplay}</span>
            </div>
          </div>
          
          {/* User info and logout */}
          {user && (
            <div className="flex items-center gap-3 px-3 py-1.5 rounded-full bg-white/[0.03] border border-white/[0.06]">
              <span className="text-xs text-muted-foreground">
                {user.email}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={logout}
                className="h-6 px-2 text-xs hover:bg-white/[0.06] hover:text-red-400 transition-colors"
              >
                Logout
              </Button>
            </div>
          )}
          
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
