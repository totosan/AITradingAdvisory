import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

/**
 * User type matching backend response
 */
export interface User {
  id: string;
  email: string;
  is_admin: boolean;
  is_active: boolean;
}

/**
 * Auth state interface
 */
interface AuthState {
  // State
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  
  // Actions
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  login: (token: string, user: User) => void;
  logout: () => void;
  clearError: () => void;
}

/**
 * Auth store with persistence (localStorage)
 * 
 * Stores auth token and user info for session persistence.
 * Token is automatically loaded on app start.
 */
export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      // Initial state
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      
      // Set user
      setUser: (user) => set({ 
        user,
        isAuthenticated: user !== null 
      }),
      
      // Set token
      setToken: (token) => set({ 
        token,
        isAuthenticated: token !== null 
      }),
      
      // Set loading state
      setLoading: (loading) => set({ isLoading: loading }),
      
      // Set error message
      setError: (error) => set({ error }),
      
      // Login - store token and user
      login: (token, user) => set({
        token,
        user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      }),
      
      // Logout - clear all auth state
      logout: () => set({
        token: null,
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      }),
      
      // Clear error
      clearError: () => set({ error: null }),
    }),
    {
      name: 'auth-storage', // localStorage key
      storage: createJSONStorage(() => localStorage),
      // Only persist token and user, not loading/error state
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

/**
 * Get the current auth token (for use outside of React components)
 */
export function getAuthToken(): string | null {
  return useAuthStore.getState().token;
}

/**
 * Check if user is authenticated (for use outside of React components)
 */
export function isAuthenticated(): boolean {
  return useAuthStore.getState().isAuthenticated;
}
