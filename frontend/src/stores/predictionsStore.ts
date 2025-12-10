/**
 * Predictions store for the Learning System
 * 
 * Manages prediction state, fetching, and caching.
 */
import { create } from 'zustand';
import type {
  Prediction,
  StrategyStats,
  GlobalInsight,
  StrategyType,
  PredictionStatus,
} from '@/types/predictions';
import {
  listPredictions,
  getStrategyStats as fetchStrategyStats,
  getGlobalInsights as fetchGlobalInsights,
  submitFeedback as sendFeedback,
  getPredictionErrorMessage,
} from '@/services/predictionsService';

interface PredictionsState {
  // Data
  predictions: Prediction[];
  strategyStats: Record<StrategyType, StrategyStats | null>;
  globalInsights: GlobalInsight[];
  
  // UI State
  isLoading: boolean;
  error: string | null;
  hasMore: boolean;
  
  // Filters
  selectedStrategy: StrategyType | null;
  selectedStatus: PredictionStatus | null;
  
  // Actions
  fetchPredictions: (reset?: boolean) => Promise<void>;
  fetchStrategyStats: (strategy: StrategyType, days?: number) => Promise<void>;
  fetchGlobalInsights: (strategy?: StrategyType) => Promise<void>;
  submitFeedback: (predictionId: string, rating: 'helpful' | 'neutral' | 'wrong', comment?: string) => Promise<boolean>;
  setFilter: (strategy: StrategyType | null, status: PredictionStatus | null) => void;
  clearError: () => void;
  reset: () => void;
}

const PREDICTIONS_PAGE_SIZE = 20;

export const usePredictionsStore = create<PredictionsState>((set, get) => ({
  // Initial state
  predictions: [],
  strategyStats: {
    range: null,
    breakout_pullback: null,
    trend_following: null,
    reversal: null,
    scalping: null,
    unknown: null,
  },
  globalInsights: [],
  isLoading: false,
  error: null,
  hasMore: false,
  selectedStrategy: null,
  selectedStatus: null,

  // Fetch predictions with pagination
  fetchPredictions: async (reset = false) => {
    const { predictions, selectedStrategy, selectedStatus } = get();
    
    set({ isLoading: true, error: null });
    
    try {
      const skip = reset ? 0 : predictions.length;
      const response = await listPredictions({
        strategy_type: selectedStrategy || undefined,
        status: selectedStatus || undefined,
        limit: PREDICTIONS_PAGE_SIZE,
        skip,
      });
      
      set({
        predictions: reset 
          ? response.predictions 
          : [...predictions, ...response.predictions],
        hasMore: response.has_more,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: getPredictionErrorMessage(error),
        isLoading: false,
      });
    }
  },

  // Fetch strategy stats
  fetchStrategyStats: async (strategy: StrategyType, days = 30) => {
    set({ isLoading: true, error: null });
    
    try {
      const stats = await fetchStrategyStats(strategy, days);
      set((state) => ({
        strategyStats: {
          ...state.strategyStats,
          [strategy]: stats,
        },
        isLoading: false,
      }));
    } catch (error) {
      set({
        error: getPredictionErrorMessage(error),
        isLoading: false,
      });
    }
  },

  // Fetch global insights
  fetchGlobalInsights: async (strategy?: StrategyType) => {
    set({ isLoading: true, error: null });
    
    try {
      const insights = await fetchGlobalInsights({
        strategy_type: strategy,
        limit: 20,
      });
      set({
        globalInsights: insights,
        isLoading: false,
      });
    } catch (error) {
      set({
        error: getPredictionErrorMessage(error),
        isLoading: false,
      });
    }
  },

  // Submit feedback
  submitFeedback: async (predictionId, rating, comment) => {
    try {
      await sendFeedback(predictionId, { rating, comment });
      
      // Update prediction in local state
      set((state) => ({
        predictions: state.predictions.map((p) =>
          p.id === predictionId
            ? { ...p, user_feedback: rating, user_comment: comment || null }
            : p
        ),
      }));
      
      return true;
    } catch (error) {
      set({ error: getPredictionErrorMessage(error) });
      return false;
    }
  },

  // Set filters
  setFilter: (strategy, status) => {
    set({
      selectedStrategy: strategy,
      selectedStatus: status,
      predictions: [], // Clear to force refetch
    });
  },

  // Clear error
  clearError: () => set({ error: null }),

  // Reset store
  reset: () => set({
    predictions: [],
    strategyStats: {
      range: null,
      breakout_pullback: null,
      trend_following: null,
      reversal: null,
      scalping: null,
      unknown: null,
    },
    globalInsights: [],
    isLoading: false,
    error: null,
    hasMore: false,
    selectedStrategy: null,
    selectedStatus: null,
  }),
}));
