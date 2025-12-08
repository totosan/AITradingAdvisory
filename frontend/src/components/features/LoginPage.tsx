/**
 * LoginPage - User authentication page
 * 
 * Provides login and registration forms with error handling.
 */
import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';
import { useAuthStore } from '@/stores/authStore';
import { authService } from '@/services/authService';

type AuthMode = 'login' | 'register';

export function LoginPage() {
  const [mode, setMode] = useState<AuthMode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [localError, setLocalError] = useState<string | null>(null);
  
  const { isLoading, error } = useAuthStore();
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    
    // Validate
    if (!email || !password) {
      setLocalError('Email and password are required');
      return;
    }
    
    if (mode === 'register') {
      if (password.length < 8) {
        setLocalError('Password must be at least 8 characters');
        return;
      }
      if (password !== confirmPassword) {
        setLocalError('Passwords do not match');
        return;
      }
    }
    
    try {
      if (mode === 'login') {
        await authService.login(email, password);
      } else {
        await authService.register(email, password);
      }
      // Success - authStore will update and app will redirect
    } catch {
      // Error is already set in authStore
    }
  };
  
  const toggleMode = () => {
    setMode(mode === 'login' ? 'register' : 'login');
    setLocalError(null);
    setConfirmPassword('');
  };
  
  const displayError = localError || error;
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4">
      <Card className="w-full max-w-md p-8 bg-slate-800 border-slate-700">
        {/* Logo/Title */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white mb-2">
            🚀 AITradingAdvisory
          </h1>
          <p className="text-slate-400">
            {mode === 'login' ? 'Sign in to your account' : 'Create a new account'}
          </p>
        </div>
        
        {/* Error Message */}
        {displayError && (
          <div className="mb-4 p-3 bg-red-900/50 border border-red-700 rounded-md text-red-200 text-sm">
            {displayError}
          </div>
        )}
        
        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-1">
              Email
            </label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              disabled={isLoading}
              className="w-full bg-slate-700 border-slate-600 text-white placeholder:text-slate-500"
            />
          </div>
          
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-1">
              Password
            </label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              disabled={isLoading}
              className="w-full bg-slate-700 border-slate-600 text-white placeholder:text-slate-500"
            />
          </div>
          
          {mode === 'register' && (
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-slate-300 mb-1">
                Confirm Password
              </label>
              <Input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                disabled={isLoading}
                className="w-full bg-slate-700 border-slate-600 text-white placeholder:text-slate-500"
              />
            </div>
          )}
          
          <Button
            type="submit"
            disabled={isLoading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2"
          >
            {isLoading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                {mode === 'login' ? 'Signing in...' : 'Creating account...'}
              </span>
            ) : (
              mode === 'login' ? 'Sign In' : 'Create Account'
            )}
          </Button>
        </form>
        
        {/* Toggle Mode */}
        <div className="mt-6 text-center text-sm text-slate-400">
          {mode === 'login' ? (
            <>
              Don't have an account?{' '}
              <button
                type="button"
                onClick={toggleMode}
                className="text-blue-400 hover:text-blue-300 font-medium"
              >
                Sign up
              </button>
            </>
          ) : (
            <>
              Already have an account?{' '}
              <button
                type="button"
                onClick={toggleMode}
                className="text-blue-400 hover:text-blue-300 font-medium"
              >
                Sign in
              </button>
            </>
          )}
        </div>
      </Card>
    </div>
  );
}

export default LoginPage;
