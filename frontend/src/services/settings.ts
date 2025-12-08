/**
 * Settings API service
 */
import type {
  ExchangeCredentials,
  ExchangeConfigStatus,
  LLMConfig,
  LLMStatus,
  SettingsStatus,
  OperationResult,
} from '@/types/settings';
import { api } from './api';

export const settingsClient = {
  // ========================================================================
  // Exchange Settings
  // ========================================================================
  
  /**
   * Get exchange configuration status
   */
  async getExchangeStatus(): Promise<ExchangeConfigStatus> {
    const { data } = await api.get<ExchangeConfigStatus>('/settings/exchange');
    return data;
  },
  
  /**
   * Save exchange credentials (encrypted)
   */
  async saveExchangeCredentials(credentials: ExchangeCredentials): Promise<OperationResult> {
    const { data } = await api.post<OperationResult>('/settings/exchange', credentials);
    return data;
  },
  
  /**
   * Delete exchange credentials
   */
  async deleteExchangeCredentials(): Promise<OperationResult> {
    const { data } = await api.delete<OperationResult>('/settings/exchange');
    return data;
  },
  
  // ========================================================================
  // LLM Settings
  // ========================================================================
  
  /**
   * Get LLM configuration status
   */
  async getLLMStatus(): Promise<LLMStatus> {
    const { data } = await api.get<LLMStatus>('/settings/llm');
    return data;
  },
  
  /**
   * Save LLM configuration
   */
  async saveLLMConfig(config: LLMConfig): Promise<OperationResult> {
    const { data } = await api.post<OperationResult>('/settings/llm', config);
    return data;
  },
  
  /**
   * Delete LLM configuration
   */
  async deleteLLMConfig(): Promise<OperationResult> {
    const { data } = await api.delete<OperationResult>('/settings/llm');
    return data;
  },
  
  // ========================================================================
  // Combined Status
  // ========================================================================
  
  /**
   * Get overall settings status
   */
  async getStatus(): Promise<SettingsStatus> {
    const { data } = await api.get<SettingsStatus>('/settings/status');
    return data;
  },
  
  /**
   * Rotate encryption key (admin operation)
   */
  async rotateVaultKey(): Promise<OperationResult> {
    const { data } = await api.post<OperationResult>('/settings/vault/rotate-key');
    return data;
  },
};

export default settingsClient;
