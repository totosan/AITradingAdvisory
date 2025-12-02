import { useMemo, useState, useCallback, useEffect } from "react";
import { PanelContainer } from "@/components/layout";
import { Button, Spinner } from "@/components/ui";
import { useChartStore } from "@/stores/chartStore";
import { RefreshCw, Trash2, TrendingUp } from "lucide-react";
import { wsService } from "@/services/websocket";

const TIMEFRAMES = ["1m", "5m", "15m", "1H", "4H", "1D"] as const;
type Timeframe = (typeof TIMEFRAMES)[number];

export function ChartPanel() {
  const { charts, selectedChart, selectChart, clearCharts } = useChartStore();
  const [refreshToken, setRefreshToken] = useState(0);
  const [activeTimeframe, setActiveTimeframe] = useState<Timeframe>("1H");
  const [isLoadingTimeframe, setIsLoadingTimeframe] = useState(false);

  const currentChart = selectedChart || charts[0];

  // Listen for interval change messages from chart iframe
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === "CHART_INTERVAL_CHANGE") {
        const { symbol, interval } = event.data;
        console.log("Chart interval change requested:", symbol, interval);
        handleTimeframeChange(interval as Timeframe, symbol);
      }
    };

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [currentChart]);

  const chartSrc = useMemo(() => {
    if (!currentChart?.url) {
      return "";
    }
    const refreshParam = currentChart.url.includes("?") ? "&" : "?";
    return `${currentChart.url}${refreshParam}v=${refreshToken}`;
  }, [currentChart, refreshToken]);

  const handleRefresh = useCallback(() => {
    setRefreshToken((prev) => prev + 1);
  }, []);

  const handleTimeframeChange = useCallback(
    (timeframe: Timeframe, symbol?: string) => {
      const chartSymbol = symbol || currentChart?.symbol;
      if (!chartSymbol) return;

      setActiveTimeframe(timeframe);
      setIsLoadingTimeframe(true);

      // Send request to backend to generate new chart with different timeframe
      const message = `Generate a chart for ${chartSymbol} with ${timeframe} timeframe`;
      wsService.sendChat(message);

      // Reset loading state after a timeout (chart will be added via websocket)
      setTimeout(() => setIsLoadingTimeframe(false), 5000);
    },
    [currentChart]
  );

  return (
    <PanelContainer
      title="📈 Charts"
      className="h-full"
      headerActions={
        charts.length > 0 && (
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={handleRefresh}
              title="Reload chart"
              className="h-8 w-8 hover:bg-white/[0.08]"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={clearCharts}
              title="Clear charts"
              className="h-8 w-8 hover:bg-red-500/10 hover:text-red-400"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        )
      }
    >
      <div className="h-full flex flex-col">
        {charts.length > 0 ? (
          <>
            {/* Chart tabs - pill style */}
            <div className="flex gap-1.5 mb-3 overflow-x-auto pb-1">
              {charts.map((chart) => (
                <button
                  key={chart.chart_id}
                  onClick={() => selectChart(chart)}
                  className={`px-3 py-1.5 text-xs rounded-full whitespace-nowrap transition-all duration-200 font-medium ${
                    chart.chart_id === currentChart?.chart_id
                      ? "bg-gradient-to-r from-emerald-500 to-cyan-500 text-slate-900 shadow-lg shadow-emerald-500/20"
                      : "bg-slate-800/60 text-slate-400 hover:bg-slate-700/60 hover:text-slate-300 border border-white/[0.06]"
                  }`}
                >
                  {chart.symbol}
                  <span className="opacity-60 ml-1">({chart.interval})</span>
                </button>
              ))}
            </div>

            {/* Timeframe selector - modern pill group */}
            {currentChart && (
              <div className="flex items-center gap-2 mb-3">
                <div className="flex items-center p-1 rounded-lg bg-slate-800/40 border border-white/[0.06]">
                  {TIMEFRAMES.map((tf) => (
                    <button
                      key={tf}
                      onClick={() => handleTimeframeChange(tf)}
                      disabled={isLoadingTimeframe}
                      className={`px-2.5 py-1 text-[11px] rounded-md transition-all duration-200 font-medium ${
                        activeTimeframe === tf || currentChart.interval === tf
                          ? "bg-emerald-500/20 text-emerald-400 shadow-sm"
                          : "text-slate-500 hover:text-slate-300 hover:bg-white/[0.05]"
                      } ${isLoadingTimeframe ? "opacity-50 cursor-wait" : ""}`}
                    >
                      {tf}
                    </button>
                  ))}
                </div>
                {isLoadingTimeframe && (
                  <div className="flex items-center gap-1.5 text-xs text-emerald-400/70">
                    <Spinner size="sm" />
                    <span>Loading...</span>
                  </div>
                )}
              </div>
            )}

            {/* Chart display with glow effect */}
            <div className="flex-1 relative group">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-emerald-500/10 to-cyan-500/10 rounded-xl blur opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
              <div className="relative h-full rounded-xl overflow-hidden border border-white/[0.08] bg-slate-900/50">
                {currentChart ? (
                  <iframe
                    key={chartSrc}
                    src={chartSrc}
                    title={`${currentChart.symbol} ${currentChart.interval} chart`}
                    className="w-full h-full border-0"
                    sandbox="allow-scripts allow-same-origin"
                  />
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground">
                    Select a chart
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <div className="relative mb-6">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-500/10 to-cyan-500/10 border border-white/[0.08] flex items-center justify-center">
                <TrendingUp className="w-8 h-8 text-emerald-400/60" />
              </div>
              <div className="absolute inset-0 bg-emerald-500/10 blur-2xl -z-10" />
            </div>
            <p className="text-sm text-foreground/70 font-medium">Charts will appear here</p>
            <p className="text-xs text-muted-foreground/50 mt-1.5">
              Ask for price charts or technical analysis
            </p>
          </div>
        )}
      </div>
    </PanelContainer>
  );
}
