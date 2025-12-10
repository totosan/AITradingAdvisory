/**
 * PerformanceDashboard - Strategy performance overview
 * 
 * Displays performance metrics for each strategy type including:
 * - Win rate
 * - Average scores
 * - Strengths/Weaknesses
 * - Global insights
 */
import { useEffect, useState } from 'react';
import { usePredictionsStore } from '@/stores/predictionsStore';
import {
  STRATEGY_DISPLAY,
  type StrategyType,
  type StrategyStats,
} from '@/types/predictions';

// All strategies to display
const STRATEGIES: StrategyType[] = [
  'range',
  'breakout_pullback',
  'trend_following',
  'reversal',
  'scalping',
];

export function PerformanceDashboard() {
  const {
    strategyStats,
    globalInsights,
    isLoading,
    error,
    fetchStrategyStats,
    fetchGlobalInsights,
    clearError,
  } = usePredictionsStore();

  const [selectedPeriod, setSelectedPeriod] = useState(30);
  const [expandedStrategy, setExpandedStrategy] = useState<StrategyType | null>(null);

  // Fetch all strategy stats on mount
  useEffect(() => {
    STRATEGIES.forEach((strategy) => {
      fetchStrategyStats(strategy, selectedPeriod);
    });
    fetchGlobalInsights();
  }, [selectedPeriod, fetchStrategyStats, fetchGlobalInsights]);

  // Calculate overall stats
  const overallStats = STRATEGIES.reduce(
    (acc, strategy) => {
      const stats = strategyStats[strategy];
      if (stats && stats.total > 0) {
        acc.totalPredictions += stats.total;
        acc.totalWins += stats.outcomes.win;
        acc.totalLosses += stats.outcomes.loss;
        acc.avgAccuracy += stats.avg_accuracy_score * stats.total;
      }
      return acc;
    },
    { totalPredictions: 0, totalWins: 0, totalLosses: 0, avgAccuracy: 0 }
  );

  const overallWinRate =
    overallStats.totalPredictions > 0
      ? ((overallStats.totalWins / (overallStats.totalWins + overallStats.totalLosses)) * 100)
      : 0;
  const overallAvgAccuracy =
    overallStats.totalPredictions > 0
      ? overallStats.avgAccuracy / overallStats.totalPredictions
      : 0;

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-lg font-semibold flex items-center gap-2">
              📈 Performance Dashboard
            </h2>
            <p className="text-sm text-gray-400 mt-1">
              Strategie-Performance der letzten {selectedPeriod} Tage
            </p>
          </div>

          {/* Period Selector */}
          <select
            value={selectedPeriod}
            onChange={(e) => setSelectedPeriod(Number(e.target.value))}
            className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
          >
            <option value={7}>7 Tage</option>
            <option value={30}>30 Tage</option>
            <option value={90}>90 Tage</option>
            <option value={365}>1 Jahr</option>
          </select>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="p-3 bg-red-900/50 border-b border-red-700">
          <div className="flex justify-between items-center">
            <span className="text-red-300 text-sm">{error}</span>
            <button onClick={clearError} className="text-red-400 hover:text-red-200 text-xs">
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Overall Stats */}
        <div className="bg-gray-800 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-400 mb-3">Gesamt-Performance</h3>
          <div className="grid grid-cols-4 gap-4">
            <StatBox
              label="Total Predictions"
              value={overallStats.totalPredictions.toString()}
              color="blue"
            />
            <StatBox
              label="Win Rate"
              value={isNaN(overallWinRate) ? '-' : `${overallWinRate.toFixed(1)}%`}
              color={overallWinRate >= 50 ? 'green' : 'red'}
            />
            <StatBox
              label="Ø Accuracy"
              value={overallAvgAccuracy > 0 ? `${overallAvgAccuracy.toFixed(0)}%` : '-'}
              color={overallAvgAccuracy >= 70 ? 'green' : 'yellow'}
            />
            <StatBox
              label="Wins / Losses"
              value={`${overallStats.totalWins} / ${overallStats.totalLosses}`}
              color="gray"
            />
          </div>
        </div>

        {/* Strategy Cards */}
        <div className="space-y-3">
          <h3 className="text-sm font-medium text-gray-400">Nach Strategie</h3>
          {STRATEGIES.map((strategy) => (
            <StrategyCard
              key={strategy}
              strategy={strategy}
              stats={strategyStats[strategy]}
              isLoading={isLoading && !strategyStats[strategy]}
              isExpanded={expandedStrategy === strategy}
              onToggle={() =>
                setExpandedStrategy(expandedStrategy === strategy ? null : strategy)
              }
            />
          ))}
        </div>

        {/* Global Insights */}
        {globalInsights.length > 0 && (
          <div className="bg-gray-800 rounded-lg p-4">
            <h3 className="text-sm font-medium text-gray-400 mb-3">
              💡 Globale Erkenntnisse
            </h3>
            <div className="space-y-2">
              {globalInsights.slice(0, 5).map((insight) => (
                <div
                  key={insight.id}
                  className="bg-gray-750 p-3 rounded text-sm"
                >
                  <p className="text-gray-200">{insight.description}</p>
                  <div className="flex gap-4 mt-2 text-xs text-gray-500">
                    <span>Konfidenz: {(insight.confidence * 100).toFixed(0)}%</span>
                    <span>Belege: {insight.evidence_count}</span>
                    {insight.source_strategy && (
                      <span>
                        Von: {STRATEGY_DISPLAY[insight.source_strategy].name}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Stat box component
function StatBox({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: 'blue' | 'green' | 'red' | 'yellow' | 'gray';
}) {
  const colorClasses = {
    blue: 'text-blue-400',
    green: 'text-green-400',
    red: 'text-red-400',
    yellow: 'text-yellow-400',
    gray: 'text-gray-300',
  };

  return (
    <div className="text-center">
      <div className={`text-2xl font-bold ${colorClasses[color]}`}>{value}</div>
      <div className="text-xs text-gray-500 mt-1">{label}</div>
    </div>
  );
}

// Strategy card component
function StrategyCard({
  strategy,
  stats,
  isLoading,
  isExpanded,
  onToggle,
}: {
  strategy: StrategyType;
  stats: StrategyStats | null;
  isLoading: boolean;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const info = STRATEGY_DISPLAY[strategy];

  if (isLoading) {
    return (
      <div className="bg-gray-800 rounded-lg p-4 animate-pulse">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{info.emoji}</span>
          <div className="flex-1">
            <div className="h-4 bg-gray-700 rounded w-1/3" />
            <div className="h-3 bg-gray-700 rounded w-1/4 mt-2" />
          </div>
        </div>
      </div>
    );
  }

  const hasData = stats && stats.total > 0;

  return (
    <div className="bg-gray-800 rounded-lg overflow-hidden">
      {/* Header */}
      <div
        className="p-4 cursor-pointer hover:bg-gray-750 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{info.emoji}</span>
            <div>
              <div className="font-medium">{info.name}</div>
              <div className="text-sm text-gray-500">
                {hasData ? `${stats.total} Predictions` : 'Keine Daten'}
              </div>
            </div>
          </div>

          {hasData && (
            <div className="flex items-center gap-4">
              <div className="text-right">
                <div
                  className={`font-bold ${
                    stats.win_rate >= 50 ? 'text-green-400' : 'text-red-400'
                  }`}
                >
                  {stats.win_rate.toFixed(1)}%
                </div>
                <div className="text-xs text-gray-500">Win Rate</div>
              </div>
              <span className="text-gray-500">{isExpanded ? '▲' : '▼'}</span>
            </div>
          )}
        </div>
      </div>

      {/* Expanded Details */}
      {isExpanded && hasData && (
        <div className="px-4 pb-4 border-t border-gray-700 pt-4 space-y-4">
          {/* Stats Grid */}
          <div className="grid grid-cols-4 gap-3 text-sm">
            <div className="bg-gray-750 p-2 rounded text-center">
              <div className="text-green-400 font-medium">{stats.outcomes.win}</div>
              <div className="text-xs text-gray-500">Wins</div>
            </div>
            <div className="bg-gray-750 p-2 rounded text-center">
              <div className="text-red-400 font-medium">{stats.outcomes.loss}</div>
              <div className="text-xs text-gray-500">Losses</div>
            </div>
            <div className="bg-gray-750 p-2 rounded text-center">
              <div className="text-gray-300 font-medium">
                {stats.avg_accuracy_score.toFixed(0)}%
              </div>
              <div className="text-xs text-gray-500">Ø Accuracy</div>
            </div>
            <div className="bg-gray-750 p-2 rounded text-center">
              <div className="text-gray-300 font-medium">
                {stats.avg_rr_achieved.toFixed(2)}
              </div>
              <div className="text-xs text-gray-500">Ø R:R</div>
            </div>
          </div>

          {/* Strengths */}
          {stats.strengths.length > 0 && (
            <div>
              <div className="text-xs text-gray-500 mb-1">✅ Stärken</div>
              <div className="space-y-1">
                {stats.strengths.map((s, i) => (
                  <div key={i} className="text-sm text-green-300 bg-green-900/20 px-2 py-1 rounded">
                    {s}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Weaknesses */}
          {stats.weaknesses.length > 0 && (
            <div>
              <div className="text-xs text-gray-500 mb-1">⚠️ Verbesserungspotential</div>
              <div className="space-y-1">
                {stats.weaknesses.map((w, i) => (
                  <div key={i} className="text-sm text-yellow-300 bg-yellow-900/20 px-2 py-1 rounded">
                    {w}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Insights */}
          {stats.insights.length > 0 && (
            <div>
              <div className="text-xs text-gray-500 mb-1">💡 Insights</div>
              <div className="space-y-1">
                {stats.insights.map((insight, i) => (
                  <div key={i} className="text-sm text-blue-300 bg-blue-900/20 px-2 py-1 rounded">
                    {insight}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default PerformanceDashboard;
