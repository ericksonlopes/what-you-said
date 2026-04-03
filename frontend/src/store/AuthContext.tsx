import React, { createContext, useContext, useState, ReactNode, useCallback, useEffect } from 'react';
import { api } from '../services/api';

interface User {
  id: string;
  email: string;
  full_name?: string;
  picture_url?: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isAuthEnabled: boolean;
  isLoading: boolean;
  login: (code: string, state?: string) => Promise<void>;
  logout: () => void;
  getLoginUrl: () => Promise<string>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { readonly children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthEnabled, setIsAuthEnabled] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const checkAuthStatus = useCallback(async () => {
    try {
      // 1. Check if auth is enabled
      const config = await api.fetchAuthConfig();
      setIsAuthEnabled(config.enable_google);

      if (!config.enable_google) {
        setIsLoading(false);
        return;
      }

      // 2. Check if we have a token and it's valid
      const token = localStorage.getItem('auth_token');
      if (token) {
        try {
          const userData = await api.fetchMe();
          setUser(userData);
        } catch (e) {
          console.error("Token invalid or expired", e);
          localStorage.removeItem('auth_token');
          setUser(null);
        }
      }
    } catch (err) {
      console.error('Error checking auth status:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuthStatus();
  }, [checkAuthStatus]);

  const login = useCallback(async (code: string, state?: string) => {
    setIsLoading(true);
    try {
      const expectedState = localStorage.getItem('oauth_state') || undefined;
      localStorage.removeItem('oauth_state');
      const result = await api.googleCallback(code, state, expectedState);
      localStorage.setItem('auth_token', result.access_token);
      setUser(result.user);
    } catch (err) {
      console.error('Login failed:', err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token');
    setUser(null);
    // Optional: redirect or reload
    globalThis.location.href = '/';
  }, []);

  const getLoginUrl = useCallback(async () => {
    const { url, state } = await api.getGoogleLoginUrl();
    localStorage.setItem('oauth_state', state);
    return url;
  }, []);

  const contextValue = React.useMemo(() => ({
    user,
    isAuthenticated: !!user,
    isAuthEnabled,
    isLoading,
    login,
    logout,
    getLoginUrl
  }), [user, isAuthEnabled, isLoading, login, logout, getLoginUrl]);

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
