import { create } from 'zustand';
import type { ChartInfo } from '@/types/api';

interface ChartState {
  // Charts list
  charts: ChartInfo[];
  
  // Selected chart for display
  selectedChart: ChartInfo | null;
  
  // Loading state
  isGenerating: boolean;
  
  // Actions
  addChart: (chart: ChartInfo) => void;
  removeChart: (chartId: string) => void;
  selectChart: (chart: ChartInfo | null) => void;
  setGenerating: (generating: boolean) => void;
  clearCharts: () => void;
}

export const useChartStore = create<ChartState>((set) => ({
  charts: [],
  selectedChart: null,
  isGenerating: false,
  
  addChart: (chart) => set((state) => ({
    charts: [chart, ...state.charts],
    selectedChart: chart, // Auto-select new chart
  })),
  
  removeChart: (chartId) => set((state) => ({
    charts: state.charts.filter((c) => c.chart_id !== chartId),
    selectedChart: state.selectedChart?.chart_id === chartId ? null : state.selectedChart,
  })),
  
  selectChart: (chart) => set({ selectedChart: chart }),
  
  setGenerating: (generating) => set({ isGenerating: generating }),
  
  clearCharts: () => set({ charts: [], selectedChart: null }),
}));
