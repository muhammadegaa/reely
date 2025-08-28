import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: refreshToken
          });

          const { access_token } = response.data;
          localStorage.setItem('access_token', access_token);

          return api(originalRequest);
        }
      } catch (refreshError) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: (userData) => api.post('/api/v1/auth/register', userData),
  login: (credentials) => {
    const formData = new FormData();
    formData.append('username', credentials.email);
    formData.append('password', credentials.password);
    return api.post('/api/v1/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  refresh: (refreshToken) => api.post('/api/v1/auth/refresh', { refresh_token: refreshToken }),
  getMe: () => api.get('/api/v1/auth/me'),
  updateProfile: (data) => api.put('/api/v1/auth/me', data),
  changePassword: (data) => api.post('/api/v1/auth/change-password', data),
  deleteAccount: () => api.delete('/api/v1/auth/me'),
  getUsage: () => api.get('/api/v1/auth/usage'),
};

// Video API
export const videoAPI = {
  trim: (formData) => api.post('/api/v1/trim', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  }),
  autoHooks: (formData) => api.post('/api/v1/auto-hooks', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  }),
  download: (downloadId) => api.get(`/api/v1/download/${downloadId}`, {
    responseType: 'blob',
  }),
  getJobs: (skip = 0, limit = 20) => api.get(`/api/v1/my-jobs?skip=${skip}&limit=${limit}`),
  cleanup: (downloadId) => api.delete(`/api/v1/cleanup/${downloadId}`),
};

// Payments API
export const paymentsAPI = {
  createCheckout: (data) => api.post('/api/v1/payments/create-checkout', data),
  createPortal: (data) => api.post('/api/v1/payments/create-portal', data),
  getSubscriptionStatus: () => api.get('/api/v1/payments/subscription-status'),
};

// System API
export const systemAPI = {
  getStats: () => api.get('/api/v1/system/stats'),
  getHealth: () => api.get('/health'),
};

export default api;