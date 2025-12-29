import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { authAPI } from '../lib/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const hasProcessedRef = useRef(false);

  const checkAuth = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      if (token) {
        const response = await authAPI.getMe();
        setUser(response.data);
      }
    } catch (error) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Process OAuth session_id from URL fragment
  const processSessionId = useCallback(async (sessionId) => {
    if (hasProcessedRef.current) return;
    hasProcessedRef.current = true;

    try {
      const response = await authAPI.getSessionData(sessionId);
      const { session_token, ...userData } = response.data;
      localStorage.setItem('token', session_token);
      localStorage.setItem('user', JSON.stringify(userData));
      setUser(userData);
      // Clear the hash and redirect to dashboard
      window.history.replaceState(null, '', window.location.pathname);
      return userData;
    } catch (error) {
      console.error('Session processing failed:', error);
      hasProcessedRef.current = false;
      throw error;
    }
  }, []);

  useEffect(() => {
    // Check for session_id in URL fragment
    const hash = window.location.hash;
    if (hash.includes('session_id=')) {
      const sessionId = hash.split('session_id=')[1]?.split('&')[0];
      if (sessionId) {
        processSessionId(sessionId);
        return;
      }
    }
    checkAuth();
  }, [checkAuth, processSessionId]);

  const login = async (email, password) => {
    const response = await authAPI.login({ email, password });
    if (response.data.requires_totp) {
      return { requires_totp: true, temp_token: response.data.temp_token };
    }
    localStorage.setItem('token', response.data.token);
    localStorage.setItem('user', JSON.stringify(response.data));
    setUser(response.data);
    return response.data;
  };

  const verifyTOTP = async (code, tempToken) => {
    const response = await authAPI.verifyTOTP(code, tempToken);
    localStorage.setItem('token', response.data.token);
    localStorage.setItem('user', JSON.stringify(response.data));
    setUser(response.data);
    return response.data;
  };

  const register = async (email, password, name) => {
    const response = await authAPI.register({ email, password, name });
    localStorage.setItem('token', response.data.token);
    localStorage.setItem('user', JSON.stringify(response.data));
    setUser(response.data);
    return response.data;
  };

  const logout = async () => {
    try {
      await authAPI.logout();
    } catch (error) {
      console.error('Logout error:', error);
    }
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
  };

  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
  const loginWithGoogle = () => {
    const redirectUrl = window.location.origin + '/dashboard';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const refreshUser = async () => {
    try {
      const response = await authAPI.getMe();
      setUser(response.data);
    } catch (error) {
      console.error('Failed to refresh user:', error);
    }
  };

  const value = {
    user,
    loading,
    login,
    verifyTOTP,
    register,
    logout,
    loginWithGoogle,
    refreshUser,
    isAuthenticated: !!user,
    setupCompleted: user?.setup_completed ?? false,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
