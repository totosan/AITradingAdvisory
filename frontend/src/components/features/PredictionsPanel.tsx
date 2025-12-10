/**
 * PredictionsPanel - Displays prediction history and performance
 * 
 * Part of the Learning System UI showing:
 * - List of past predictions with outcomes
 * - Strategy performance metrics
 * - User feedback submission
 */
import { useEffect, useState } from 'react';
import { usePredictionsStore } from '@/stores/predictionsStore';
import {
  STRATEGY_DISPLAY,
  STATUS_DISPLAY,
  OUTCOME_DISPLAY,
  type StrategyType,
  type PredictionStatus,
  type Prediction,
} from '@/types/predictions';

// Strategy filter buttons
const STRATEGIES: (StrategyType | 'all')[] = [
  'all',
  'range',
  'breakout_pullback',
  'trend_following',
  'reversal',
  'scalping',
];

// Status filter buttons
const STATUSES: (PredictionStatus | 'all')[] = [
  'all',
  'active',
  'closed',
  'pending',
];

export function PredictionsPanel() {
  const {
    predictions,
    isLoading,
    error,
    hasMore,
    selectedStrategy,
    selectedStatus,
    fetchPredictions,
    setFilter,
    clearError,
  } = usePredictionsStore();

  // Fetch on mount and filter change
  useEffect(() => {
    fetchPredictions(true);
  }, [selectedStrategy, selectedStatus, fetchPredictions]);

  const handleStrategyFilter = (strategy: StrategyType | 'all') => {
    setFilter(
      strategy === 'all' ? null : strategy,
      selectedStatus
    );
  };

  const handleStatusFilter = (status: PredictionStatus | 'all') => {
    setFilter(
      selectedStrategy,
      status === 'all' ? null : status
    );
  };

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          📊 Predictions & Performance
        </h2>
        <p className="text-sm text-gray-400 mt-1">
          Deine Trading-Predictions und deren Ergebnisse
        </p>
      </div>

      {/* Filters */}
      <div className="p-3 border-b border-gray-700 space-y-2">
        {/* Strategy Filter */}
        <div className="flex flex-wrap gap-1">
          {STRATEGIES.map((strategy) => (
            <button
              key={strategy}
              onClick={() => handleStrategyFilter(strategy)}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                (strategy === 'all' && !selectedStrategy) ||
                strategy === selectedStrategy
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {strategy === 'all'
                ? 'Alle'
                : `${STRATEGY_DISPLAY[strategy].emoji} ${STRATEGY_DISPLAY[strategy].name}`}
            </button>
          ))}
        </div>

        {/* Status Filter */}
        <div className="flex flex-wrap gap-1">
          {STATUSES.map((status) => (
            <button
              key={status}
              onClick={() => handleStatusFilter(status)}
              className={`px-2 py-1 text-xs rounded transition-colors ${
                (status === 'all' && !selectedStatus) ||
                status === selectedStatus
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {status === 'all' ? 'Alle Status' : STATUS_DISPLAY[status].name}
            </button>
          ))}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-3 bg-red-900/50 border-b border-red-700">
          <div className="flex justify-between items-center">
            <span className="text-red-300 text-sm">{error}</span>
            <button
              onClick={clearError}
              className="text-red-400 hover:text-red-200 text-xs"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Predictions List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {predictions.length === 0 && !isLoading && (
          <div className="text-center text-gray-500 py-8">
            <p className="text-4xl mb-2">📭</p>
            <p>Keine Predictions gefunden</p>
            <p className="text-sm mt-1">
              Starte eine Analyse um Predictions zu erstellen
            </p>
          </div>
        )}

        {predictions.map((prediction) => (
          <PredictionCard key={prediction.id} prediction={prediction} />
        ))}

        {/* Load More */}
        {hasMore && (
          <button
            onClick={() => fetchPredictions()}
            disabled={isLoading}
            className="w-full py-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            {isLoading ? 'Laden...' : 'Mehr laden'}
          </button>
        )}

        {isLoading && predictions.length === 0 && (
          <div className="text-center text-gray-500 py-8">
            <div className="animate-spin inline-block w-8 h-8 border-2 border-gray-400 border-t-transparent rounded-full" />
            <p className="mt-2">Lade Predictions...</p>
          </div>
        )}
      </div>
    </div>
  );
}

// Individual prediction card
function PredictionCard({ prediction }: { prediction: Prediction }) {
  const [showDetails, setShowDetails] = useState(false);
  const { submitFeedback } = usePredictionsStore();
  const [feedbackLoading, setFeedbackLoading] = useState(false);

  const strategyInfo = STRATEGY_DISPLAY[prediction.strategy_type];
  const statusInfo = STATUS_DISPLAY[prediction.status];
  const outcomeInfo = prediction.outcome ? OUTCOME_DISPLAY[prediction.outcome] : null;

  const handleFeedback = async (rating: 'helpful' | 'neutral' | 'wrong') => {
    setFeedbackLoading(true);
    await submitFeedback(prediction.id, rating);
    setFeedbackLoading(false);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('de-DE', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatPrice = (price: number) => {
    if (price >= 1000) return price.toLocaleString('de-DE', { maximumFractionDigits: 0 });
    if (price >= 1) return price.toLocaleString('de-DE', { maximumFractionDigits: 2 });
    return price.toLocaleString('de-DE', { maximumFractionDigits: 6 });
  };

  return (
    <div
      className={`bg-gray-800 rounded-lg border transition-colors ${
        prediction.status === 'active'
          ? 'border-blue-500'
          : prediction.outcome === 'win'
          ? 'border-green-600/50'
          : prediction.outcome === 'loss'
          ? 'border-red-600/50'
          : 'border-gray-700'
      }`}
    >
      {/* Header */}
      <div
        className="p-3 cursor-pointer hover:bg-gray-750"
        onClick={() => setShowDetails(!showDetails)}
      >
        <div className="flex justify-between items-start">
          <div className="flex items-center gap-2">
            <span className="text-lg">{strategyInfo.emoji}</span>
            <div>
              <span className="font-medium">{prediction.symbol}</span>
              <span
                className={`ml-2 text-sm ${
                  prediction.direction === 'long' ? 'text-green-400' : 'text-red-400'
                }`}
              >
                {prediction.direction.toUpperCase()}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {outcomeInfo && (
              <span className={`text-sm ${
                prediction.outcome === 'win' ? 'text-green-400' :
                prediction.outcome === 'loss' ? 'text-red-400' : 'text-gray-400'
              }`}>
                {outcomeInfo.emoji}
              </span>
            )}
            <span
              className={`text-xs px-2 py-0.5 rounded ${
                prediction.status === 'active'
                  ? 'bg-blue-600'
                  : prediction.status === 'closed'
                  ? 'bg-gray-600'
                  : 'bg-gray-700'
              }`}
            >
              {statusInfo.name}
            </span>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="flex gap-4 mt-2 text-sm text-gray-400">
          <span>Entry: ${formatPrice(prediction.entry_price)}</span>
          <span>SL: ${formatPrice(prediction.stop_loss)}</span>
          {prediction.accuracy_score !== null && (
            <span className={prediction.accuracy_score >= 70 ? 'text-green-400' : ''}>
              Score: {prediction.accuracy_score.toFixed(0)}%
            </span>
          )}
        </div>
      </div>

      {/* Details (expanded) */}
      {showDetails && (
        <div className="px-3 pb-3 border-t border-gray-700 pt-3 space-y-3">
          {/* Trade Details */}
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-gray-500">Strategy:</span>
              <span className="ml-2">{strategyInfo.name}</span>
            </div>
            <div>
              <span className="text-gray-500">Timeframe:</span>
              <span className="ml-2">{prediction.timeframe}</span>
            </div>
            <div>
              <span className="text-gray-500">Take Profits:</span>
              <span className="ml-2">
                {prediction.take_profit.map((tp) => `$${formatPrice(tp)}`).join(', ')}
              </span>
            </div>
            <div>
              <span className="text-gray-500">Confidence:</span>
              <span className="ml-2">{prediction.confidence}</span>
            </div>
          </div>

          {/* Signals */}
          {prediction.signals.length > 0 && (
            <div>
              <span className="text-gray-500 text-sm">Signale:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {prediction.signals.map((signal, i) => (
                  <span
                    key={i}
                    className="text-xs bg-gray-700 px-2 py-0.5 rounded"
                  >
                    {signal}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Scores (if closed) */}
          {prediction.status === 'closed' && (
            <div className="grid grid-cols-3 gap-2 text-sm">
              {prediction.accuracy_score !== null && (
                <div className="bg-gray-750 p-2 rounded text-center">
                  <div className="text-gray-500 text-xs">Accuracy</div>
                  <div className={prediction.accuracy_score >= 70 ? 'text-green-400' : ''}>
                    {prediction.accuracy_score.toFixed(0)}%
                  </div>
                </div>
              )}
              {prediction.timing_score !== null && (
                <div className="bg-gray-750 p-2 rounded text-center">
                  <div className="text-gray-500 text-xs">Timing</div>
                  <div>{prediction.timing_score.toFixed(0)}%</div>
                </div>
              )}
              {prediction.rr_achieved !== null && (
                <div className="bg-gray-750 p-2 rounded text-center">
                  <div className="text-gray-500 text-xs">R:R</div>
                  <div>{prediction.rr_achieved.toFixed(2)}</div>
                </div>
              )}
            </div>
          )}

          {/* Feedback */}
          {prediction.status === 'closed' && !prediction.user_feedback && (
            <div className="pt-2 border-t border-gray-700">
              <span className="text-sm text-gray-400">War diese Analyse hilfreich?</span>
              <div className="flex gap-2 mt-2">
                <button
                  onClick={() => handleFeedback('helpful')}
                  disabled={feedbackLoading}
                  className="flex-1 py-1 text-sm bg-green-600/30 hover:bg-green-600/50 text-green-400 rounded transition-colors"
                >
                  👍 Hilfreich
                </button>
                <button
                  onClick={() => handleFeedback('neutral')}
                  disabled={feedbackLoading}
                  className="flex-1 py-1 text-sm bg-gray-600/30 hover:bg-gray-600/50 text-gray-400 rounded transition-colors"
                >
                  😐 Neutral
                </button>
                <button
                  onClick={() => handleFeedback('wrong')}
                  disabled={feedbackLoading}
                  className="flex-1 py-1 text-sm bg-red-600/30 hover:bg-red-600/50 text-red-400 rounded transition-colors"
                >
                  👎 Falsch
                </button>
              </div>
            </div>
          )}

          {/* Existing Feedback */}
          {prediction.user_feedback && (
            <div className="text-sm text-gray-500">
              Dein Feedback: <span className="text-gray-300">{prediction.user_feedback}</span>
            </div>
          )}

          {/* Timestamp */}
          <div className="text-xs text-gray-600">
            Erstellt: {formatDate(prediction.created_at)}
          </div>
        </div>
      )}
    </div>
  );
}

export default PredictionsPanel;
