/**
 * ProtectedRoute - Wrapper component that requires authentication
 * 
 * Redirects unauthenticated users to login page.
 * Shows loading state while validating session.
 */
import { useEffect, useState } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { authService } from '@/services/authService';
import { LoginPage } from '@/components/features/LoginPage';
import { Spinner } from '@/components/ui/Spinner';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, token } = useAuthStore();
  const [isValidating, setIsValidating] = useState(true);
  
  useEffect(() => {
    const validateSession = async () => {
      if (token) {
        // Token exists, validate it
        await authService.validateSession();
      }
      setIsValidating(false);
    };
    
    validateSession();
  }, [token]);
  
  // Show loading while validating
  if (isValidating && token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-900">
        <div className="text-center">
          <Spinner className="h-8 w-8 text-blue-500 mx-auto mb-4" />
          <p className="text-slate-400">Validating session...</p>
        </div>
      </div>
    );
  }
  
  // Not authenticated - show login
  if (!isAuthenticated) {
    return <LoginPage />;
  }
  
  // Authenticated - render children
  return <>{children}</>;
}

export default ProtectedRoute;
