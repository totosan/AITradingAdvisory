/**
 * Predictions service for the Learning System
 * 
 * Handles API calls to prediction endpoints.
 */
import axios, { AxiosError } from 'axios';
import { useAuthStore } from '@/stores/authStore';
import type {
  Prediction,
  PredictionListResponse,
  StrategyStats,
  GlobalInsight,
  FeedbackRequest,
  FeedbackResponse,
  StrategyType,
  PredictionStatus,
} from '@/types/predictions';

// Base API URL
const API_BASE = '/api/v1';

/**
 * Create axios instance for prediction requests
 */
const predictionsApi = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
predictionsApi.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
predictionsApi.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
    }
    return Promise.reject(error);
  }
);

/**
 * List predictions with optional filters
 */
export async function listPredictions(params?: {
  strategy_type?: StrategyType;
  status?: PredictionStatus;
  limit?: number;
  skip?: number;
}): Promise<PredictionListResponse> {
  const response = await predictionsApi.get<PredictionListResponse>('/predictions/', { params });
  return response.data;
}

/**
 * Get a single prediction by ID
 */
export async function getPrediction(predictionId: string): Promise<Prediction> {
  const response = await predictionsApi.get<Prediction>(`/predictions/${predictionId}`);
  return response.data;
}

/**
 * Get strategy performance statistics
 */
export async function getStrategyStats(
  strategyType: StrategyType,
  days: number = 30
): Promise<StrategyStats> {
  const response = await predictionsApi.get<StrategyStats>('/predictions/stats', {
    params: { strategy_type: strategyType, days },
  });
  return response.data;
}

/**
 * Submit feedback for a prediction
 */
export async function submitFeedback(
  predictionId: string,
  feedback: FeedbackRequest
): Promise<FeedbackResponse> {
  const response = await predictionsApi.post<FeedbackResponse>(
    `/predictions/${predictionId}/feedback`,
    feedback
  );
  return response.data;
}

/**
 * Get global insights
 */
export async function getGlobalInsights(params?: {
  strategy_type?: StrategyType;
  limit?: number;
}): Promise<GlobalInsight[]> {
  const response = await predictionsApi.get<GlobalInsight[]>('/predictions/insights/global', {
    params,
  });
  return response.data;
}

/**
 * Error helper
 */
export function getPredictionErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (error.response?.status === 401) return 'Nicht authentifiziert';
    if (error.response?.status === 404) return 'Prediction nicht gefunden';
    if (error.response?.status === 500) return 'Serverfehler';
  }
  return 'Ein unbekannter Fehler ist aufgetreten';
}
