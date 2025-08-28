import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 900000, // 15 minute timeout for long videos
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('reely_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        const refreshToken = localStorage.getItem('reely_refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken
          });
          
          const { access_token } = response.data;
          localStorage.setItem('reely_token', access_token);
          
          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, logout user
        localStorage.removeItem('reely_token');
        localStorage.removeItem('reely_refresh_token');
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: async (email, password) => {
    const formData = new FormData();
    formData.append('email', email);
    formData.append('password', password);
    
    const response = await api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },

  register: async (email, password, fullName) => {
    const response = await api.post('/auth/register', {
      email,
      password,
      full_name: fullName
    });
    return response.data;
  },

  refreshToken: async (refreshToken) => {
    const response = await api.post('/auth/refresh', {
      refresh_token: refreshToken
    });
    return response.data;
  },

  getProfile: async () => {
    const response = await api.get('/auth/profile');
    return response.data;
  },

  updateProfile: async (profileData) => {
    const response = await api.put('/auth/profile', profileData);
    return response.data;
  },

  getUsage: async () => {
    const response = await api.get('/auth/usage');
    return response.data;
  },

  getApiKeys: async () => {
    const response = await api.get('/auth/api-keys');
    return response.data;
  },

  createApiKey: async (name) => {
    const response = await api.post('/auth/api-keys', { name });
    return response.data;
  },

  deleteApiKey: async (keyId) => {
    const response = await api.delete(`/auth/api-keys/${keyId}`);
    return response.data;
  }
};

// Video API
export const videoAPI = {
  trim: async (formData) => {
    const response = await api.post('/api/v1/trim', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },

  autoHooks: async (url, aiProvider = 'openai', asyncProcessing = true) => {
    const formData = new FormData();
    formData.append('url', url);
    formData.append('ai_provider', aiProvider);
    formData.append('async_processing', asyncProcessing);
    
    const response = await api.post('/api/v1/auto-hooks', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  },

  getJobs: async (page = 1, limit = 10) => {
    const response = await api.get(`/jobs?page=${page}&limit=${limit}`);
    return response.data;
  },

  getJob: async (jobId) => {
    const response = await api.get(`/api/v1/my-jobs`);
    return response.data;
  },

  getJobStatus: async (jobId) => {
    const response = await api.get(`/api/v1/jobs/${jobId}/status`);
    return response.data;
  },

  cancelJob: async (jobId) => {
    const response = await api.post(`/api/v1/jobs/${jobId}/cancel`);
    return response.data;
  },

  downloadVideo: (downloadId) => {
    return `${API_BASE_URL}/download/${downloadId}`;
  },

  deleteJob: async (jobId) => {
    const response = await api.delete(`/jobs/${jobId}`);
    return response.data;
  }
};

// Subscription API
export const subscriptionAPI = {
  createCheckoutSession: async (priceId) => {
    const response = await api.post('/payments/create-checkout-session', {
      price_id: priceId
    });
    return response.data;
  },

  createPortalSession: async () => {
    const response = await api.post('/payments/create-portal-session');
    return response.data;
  },

  getSubscription: async () => {
    const response = await api.get('/payments/subscription');
    return response.data;
  }
};

// Health API
export const healthAPI = {
  check: async () => {
    const response = await api.get('/health');
    return response.data;
  }
};

export default api;