import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext({});

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('reely_token'));

  // Initialize auth state on app load
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('reely_token');
      if (storedToken) {
        try {
          const profile = await authAPI.getProfile();
          setUser(profile);
          setToken(storedToken);
        } catch (error) {
          console.error('Failed to initialize auth:', error);
          localStorage.removeItem('reely_token');
          localStorage.removeItem('reely_refresh_token');
          setToken(null);
        }
      }
      setLoading(false);
    };

    initAuth();
  }, []);

  const login = async (email, password) => {
    try {
      const response = await authAPI.login(email, password);
      const { access_token, refresh_token, user: userData } = response;
      
      localStorage.setItem('reely_token', access_token);
      localStorage.setItem('reely_refresh_token', refresh_token);
      setToken(access_token);
      setUser(userData);
      
      return { success: true };
    } catch (error) {
      console.error('Login failed:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Login failed' 
      };
    }
  };

  const register = async (email, password, fullName) => {
    try {
      const response = await authAPI.register(email, password, fullName);
      const { access_token, refresh_token, user: userData } = response;
      
      localStorage.setItem('reely_token', access_token);
      localStorage.setItem('reely_refresh_token', refresh_token);
      setToken(access_token);
      setUser(userData);
      
      return { success: true };
    } catch (error) {
      console.error('Registration failed:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Registration failed' 
      };
    }
  };

  const logout = () => {
    localStorage.removeItem('reely_token');
    localStorage.removeItem('reely_refresh_token');
    setToken(null);
    setUser(null);
  };

  const refreshToken = async () => {
    try {
      const refreshToken = localStorage.getItem('reely_refresh_token');
      if (!refreshToken) throw new Error('No refresh token');

      const response = await authAPI.refreshToken(refreshToken);
      const { access_token } = response;
      
      localStorage.setItem('reely_token', access_token);
      setToken(access_token);
      
      return access_token;
    } catch (error) {
      console.error('Token refresh failed:', error);
      logout();
      throw error;
    }
  };

  const updateProfile = async (profileData) => {
    try {
      const updatedUser = await authAPI.updateProfile(profileData);
      setUser(updatedUser);
      return { success: true };
    } catch (error) {
      console.error('Profile update failed:', error);
      return { 
        success: false, 
        error: error.response?.data?.detail || 'Profile update failed' 
      };
    }
  };

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!token && !!user,
    login,
    register,
    logout,
    refreshToken,
    updateProfile
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};