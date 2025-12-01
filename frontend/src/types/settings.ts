/**
 * Settings types matching backend models
 */

// Exchange types
export interface ExchangeCredentials {
  api_key: string;
  api_secret: string;
  passphrase: string;
}

export interface ExchangeConfigStatus {
  configured: boolean;
  provider: string;
  api_key_masked: string | null;
}

// LLM types
export interface LLMConfig {
  provider: 'ollama' | 'azure';
  model?: string;
  base_url?: string;
  api_key?: string;
  endpoint?: string;
}

export interface LLMStatus {
  provider: string;
  model?: string;
  azure_configured?: boolean;
  endpoint_masked?: string;
}

// Combined status
export interface SettingsStatus {
  exchange: ExchangeConfigStatus;
  llm: LLMStatus;
  vault_status: {
    vault_path: string;
    secrets_count: number;
    encryption_enabled: boolean;
  };
}

// Operation result
export interface OperationResult {
  status: 'success' | 'warning' | 'error';
  message: string;
  validation?: {
    valid: boolean;
    message?: string;
  };
}
