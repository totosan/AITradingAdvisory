/**
 * Settings API service
 */
import axios from 'axios';
import type {
  ExchangeCredentials,
  ExchangeConfigStatus,
  LLMConfig,
  LLMStatus,
  SettingsStatus,
  OperationResult,
} from '@/types/settings';

// Create axios instance with base URL
const api = axios.create({
  baseURL: '/api/v1/settings',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const settingsClient = {
  // ========================================================================
  // Exchange Settings
  // ========================================================================
  
  /**
   * Get exchange configuration status
   */
  async getExchangeStatus(): Promise<ExchangeConfigStatus> {
    const { data } = await api.get<ExchangeConfigStatus>('/exchange');
    return data;
  },
  
  /**
   * Save exchange credentials (encrypted)
   */
  async saveExchangeCredentials(credentials: ExchangeCredentials): Promise<OperationResult> {
    const { data } = await api.post<OperationResult>('/exchange', credentials);
    return data;
  },
  
  /**
   * Delete exchange credentials
   */
  async deleteExchangeCredentials(): Promise<OperationResult> {
    const { data } = await api.delete<OperationResult>('/exchange');
    return data;
  },
  
  // ========================================================================
  // LLM Settings
  // ========================================================================
  
  /**
   * Get LLM configuration status
   */
  async getLLMStatus(): Promise<LLMStatus> {
    const { data } = await api.get<LLMStatus>('/llm');
    return data;
  },
  
  /**
   * Save LLM configuration
   */
  async saveLLMConfig(config: LLMConfig): Promise<OperationResult> {
    const { data } = await api.post<OperationResult>('/llm', config);
    return data;
  },
  
  /**
   * Delete LLM configuration
   */
  async deleteLLMConfig(): Promise<OperationResult> {
    const { data } = await api.delete<OperationResult>('/llm');
    return data;
  },
  
  // ========================================================================
  // Combined Status
  // ========================================================================
  
  /**
   * Get overall settings status
   */
  async getStatus(): Promise<SettingsStatus> {
    const { data } = await api.get<SettingsStatus>('/status');
    return data;
  },
  
  /**
   * Rotate encryption key (admin operation)
   */
  async rotateVaultKey(): Promise<OperationResult> {
    const { data } = await api.post<OperationResult>('/vault/rotate-key');
    return data;
  },
};

export default settingsClient;
