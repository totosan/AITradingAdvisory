declare global {
  interface Window {
    RUNTIME_CONFIG?: {
      API_URL?: string;
      WS_URL?: string;
    };
  }
}

export {};
