import { PanelContainer } from "@/components/layout";
import { Button } from "@/components/ui";
import { useChartStore } from "@/stores/chartStore";
import { RefreshCw } from "lucide-react";

export function ChartPanel() {
  const { charts, selectedChart, selectChart, clearCharts } = useChartStore();

  const currentChart = selectedChart || charts[0];

  return (
    <PanelContainer
      title="📈 Charts"
      className="h-full"
      headerActions={
        charts.length > 0 && (
          <Button variant="ghost" size="icon" onClick={clearCharts}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        )
      }
    >
      <div className="h-full flex flex-col">
        {charts.length > 0 ? (
          <>
            {/* Chart tabs */}
            <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
              {charts.map((chart) => (
                <button
                  key={chart.chart_id}
                  onClick={() => selectChart(chart)}
                  className={`px-3 py-1.5 text-xs rounded-md whitespace-nowrap transition-colors ${
                    chart.chart_id === currentChart?.chart_id
                      ? "bg-primary text-primary-foreground"
                      : "bg-secondary/50 text-muted-foreground hover:bg-secondary"
                  }`}
                >
                  {chart.symbol} ({chart.interval})
                </button>
              ))}
            </div>

            {/* Chart display */}
            <div className="flex-1 rounded-lg overflow-hidden border border-border bg-background/50">
              {currentChart ? (
                <iframe
                  src={currentChart.url}
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
          </>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground py-8">
            <span className="text-4xl mb-4">📈</span>
            <p className="text-sm">Charts will appear here</p>
            <p className="text-xs mt-2">
              Ask for price charts or technical analysis
            </p>
          </div>
        )}
      </div>
    </PanelContainer>
  );
}
