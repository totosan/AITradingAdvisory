import axios from 'axios';
import type {
  ApiInfo,
  HealthResponse,
  ReadinessResponse,
  WsStatusResponse,
  ConversationInfo,
  ChartInfo,
  ChartRequest,
} from '@/types/api';
import { getAuthToken, useAuthStore } from '@/stores/authStore';

// Create axios instance with base URL
export const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to all requests
api.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 errors (logout on token expiry)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      // Token expired - logout
      useAuthStore.getState().logout();
    }
    return Promise.reject(error);
  }
);

// API client
export const apiClient = {
  // Root info
  async getInfo(): Promise<ApiInfo> {
    const { data } = await axios.get<ApiInfo>('/');
    return data;
  },
  
  // Health checks
  async getHealth(): Promise<HealthResponse> {
    const { data } = await api.get<HealthResponse>('/health');
    return data;
  },
  
  async getReadiness(): Promise<ReadinessResponse> {
    const { data } = await api.get<ReadinessResponse>('/health/ready');
    return data;
  },
  
  // WebSocket status
  async getWsStatus(): Promise<WsStatusResponse> {
    const { data } = await axios.get<WsStatusResponse>('/ws/status');
    return data;
  },
  
  // Conversations
  async listConversations(): Promise<ConversationInfo[]> {
    const { data } = await api.get<ConversationInfo[]>('/chat/');
    return data;
  },
  
  async createConversation(title?: string): Promise<ConversationInfo> {
    const { data } = await api.post<ConversationInfo>('/chat/new', { title });
    return data;
  },
  
  async deleteConversation(id: string): Promise<void> {
    await api.delete(`/chat/${id}`);
  },
  
  // Charts
  async listCharts(symbol?: string): Promise<ChartInfo[]> {
    const params = symbol ? { symbol } : {};
    const { data } = await api.get<ChartInfo[]>('/charts/', { params });
    return data;
  },
  
  async generateChart(request: ChartRequest): Promise<ChartInfo> {
    const { data } = await api.post<ChartInfo>('/charts/', request);
    return data;
  },
  
  async generateMultiTimeframeChart(symbol: string, timeframes: string): Promise<ChartInfo> {
    const { data } = await api.post<ChartInfo>('/charts/multi-timeframe', null, {
      params: { symbol, timeframes },
    });
    return data;
  },
  
  async generateAlertsDashboard(symbol: string): Promise<ChartInfo> {
    const { data } = await api.post<ChartInfo>('/charts/alerts-dashboard', null, {
      params: { symbol },
    });
    return data;
  },
  
  async deleteChart(id: string): Promise<void> {
    await api.delete(`/charts/${id}`);
  },
};

export default apiClient;
