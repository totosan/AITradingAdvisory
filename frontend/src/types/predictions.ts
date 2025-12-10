/**
 * TypeScript types for the Learning System / Predictions API
 */

// Strategy types matching backend StrategyType enum
export type StrategyType = 
  | "range"
  | "breakout_pullback"
  | "trend_following"
  | "reversal"
  | "scalping"
  | "unknown";

// Prediction status
export type PredictionStatus = "pending" | "active" | "closed" | "expired" | "cancelled";

// Prediction outcome
export type PredictionOutcome = "win" | "loss" | "break_even" | "expired";

// Single prediction
export interface Prediction {
  id: string;
  strategy_type: StrategyType;
  symbol: string;
  direction: "long" | "short";
  entry_price: number;
  stop_loss: number;
  take_profit: number[];
  timeframe: string;
  confidence: string;
  signals: string[];
  analysis_summary: string | null;
  status: PredictionStatus;
  outcome: PredictionOutcome | null;
  actual_exit_price: number | null;
  accuracy_score: number | null;
  timing_score: number | null;
  rr_achieved: number | null;
  user_feedback: string | null;
  user_comment: string | null;
  created_at: string;
  activated_at: string | null;
  closed_at: string | null;
  valid_until: string | null;
}

// Prediction list response
export interface PredictionListResponse {
  predictions: Prediction[];
  total: number;
  has_more: boolean;
}

// Strategy performance stats
export interface StrategyStats {
  strategy_type: StrategyType;
  period_days: number;
  total: number;
  active_count: number;
  win_rate: number;
  avg_accuracy_score: number;
  avg_rr_achieved: number;
  outcomes: {
    win: number;
    loss: number;
    break_even: number;
    expired: number;
  };
  strengths: string[];
  weaknesses: string[];
  insights: string[];
}

// Global insight
export interface GlobalInsight {
  id: string;
  insight_type: string;
  description: string;
  source_strategy: StrategyType | null;
  applies_to_all: boolean;
  confidence: number;
  evidence_count: number;
  created_at: string;
}

// Feedback request
export interface FeedbackRequest {
  rating: "helpful" | "neutral" | "wrong";
  comment?: string;
}

// Feedback response
export interface FeedbackResponse {
  success: boolean;
  message: string;
}

// Strategy display info
export const STRATEGY_DISPLAY: Record<StrategyType, { name: string; emoji: string; color: string }> = {
  range: { name: "Range Trading", emoji: "📊", color: "blue" },
  breakout_pullback: { name: "Breakout Pullback", emoji: "🚀", color: "orange" },
  trend_following: { name: "Trend Following", emoji: "📈", color: "green" },
  reversal: { name: "Reversal", emoji: "🔄", color: "purple" },
  scalping: { name: "Scalping", emoji: "⚡", color: "yellow" },
  unknown: { name: "Unbekannt", emoji: "❓", color: "gray" },
};

// Status display info
export const STATUS_DISPLAY: Record<PredictionStatus, { name: string; color: string }> = {
  pending: { name: "Ausstehend", color: "gray" },
  active: { name: "Aktiv", color: "blue" },
  closed: { name: "Abgeschlossen", color: "green" },
  expired: { name: "Abgelaufen", color: "yellow" },
  cancelled: { name: "Abgebrochen", color: "red" },
};

// Outcome display info
export const OUTCOME_DISPLAY: Record<PredictionOutcome, { name: string; emoji: string; color: string }> = {
  win: { name: "Gewinn", emoji: "✅", color: "green" },
  loss: { name: "Verlust", emoji: "❌", color: "red" },
  break_even: { name: "Break Even", emoji: "➖", color: "yellow" },
  expired: { name: "Abgelaufen", emoji: "⏰", color: "gray" },
};
