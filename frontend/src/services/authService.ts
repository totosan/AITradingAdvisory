/**
 * Authentication service for user login/registration
 * 
 * Handles API calls to auth endpoints and integrates with authStore.
 */
import axios, { AxiosError } from 'axios';
import { useAuthStore, type User } from '@/stores/authStore';

// Base API URL
const API_BASE = '/api/v1';

/**
 * Request types
 */
export interface RegisterRequest {
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

/**
 * Response types
 */
export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface AuthError {
  detail: string;
}

/**
 * Create axios instance for auth requests
 */
const authApi = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Add auth token to requests if available
 */
authApi.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * Handle auth errors (401 = logout)
 */
authApi.interceptors.response.use(
  (response) => response,
  (error: AxiosError<AuthError>) => {
    if (error.response?.status === 401) {
      // Token expired or invalid - logout
      useAuthStore.getState().logout();
    }
    return Promise.reject(error);
  }
);

/**
 * Auth service functions
 */
export const authService = {
  /**
   * Register a new user
   */
  async register(email: string, password: string): Promise<AuthResponse> {
    const store = useAuthStore.getState();
    store.setLoading(true);
    store.clearError();
    
    try {
      const { data } = await authApi.post<AuthResponse>('/auth/register', {
        email,
        password,
      });
      
      // Store token and user
      store.login(data.access_token, data.user);
      
      return data;
    } catch (error) {
      const axiosError = error as AxiosError<AuthError>;
      const message = axiosError.response?.data?.detail || 'Registration failed';
      store.setError(message);
      store.setLoading(false);
      throw new Error(message);
    }
  },
  
  /**
   * Login an existing user
   */
  async login(email: string, password: string): Promise<AuthResponse> {
    const store = useAuthStore.getState();
    store.setLoading(true);
    store.clearError();
    
    try {
      const { data } = await authApi.post<AuthResponse>('/auth/login', {
        email,
        password,
      });
      
      // Store token and user
      store.login(data.access_token, data.user);
      
      return data;
    } catch (error) {
      const axiosError = error as AxiosError<AuthError>;
      const message = axiosError.response?.data?.detail || 'Login failed';
      store.setError(message);
      store.setLoading(false);
      throw new Error(message);
    }
  },
  
  /**
   * Get current user info (validates token)
   */
  async getCurrentUser(): Promise<User> {
    const { data } = await authApi.get<User>('/auth/me');
    useAuthStore.getState().setUser(data);
    return data;
  },
  
  /**
   * Logout the current user
   */
  logout(): void {
    useAuthStore.getState().logout();
  },
  
  /**
   * Check if a token exists and is still valid
   * Call this on app startup to restore session
   */
  async validateSession(): Promise<boolean> {
    const store = useAuthStore.getState();
    
    if (!store.token) {
      return false;
    }
    
    try {
      await authService.getCurrentUser();
      return true;
    } catch {
      // Token is invalid - clear it
      store.logout();
      return false;
    }
  },
};

export default authService;
