import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const api = axios.create({
  baseURL: `${API_URL}/api`,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  verifyTOTP: (code, tempToken) => api.post('/auth/verify-totp', { code }, { headers: { Authorization: `Bearer ${tempToken}` } }),
  getSessionData: (sessionId) => api.get('/auth/session-data', { headers: { 'X-Session-ID': sessionId } }),
  getMe: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout'),
  setupTOTP: () => api.post('/auth/totp/setup'),
  verifyTOTPSetup: (code) => api.post('/auth/totp/verify', { code }),
  disableTOTP: (code) => api.post('/auth/totp/disable', { code }),
};

// Profile API
export const profileAPI = {
  get: () => api.get('/profile'),
  create: (data) => api.post('/profile', data),
  update: (data) => api.put('/profile', data),
};

// Dashboard API
export const dashboardAPI = {
  get: () => api.get('/dashboard'),
};

// Transactions API
export const transactionsAPI = {
  getAll: (limit = 100, skip = 0) => api.get(`/transactions?limit=${limit}&skip=${skip}`),
  create: (data) => api.post('/transactions', data),
  delete: (id) => api.delete(`/transactions/${id}`),
};

// Mileage API
export const mileageAPI = {
  getAll: () => api.get('/mileage'),
  create: (data) => api.post('/mileage', data),
  delete: (id) => api.delete(`/mileage/${id}`),
};

// Charging API
export const chargingAPI = {
  getAll: () => api.get('/charging'),
  create: (data) => api.post('/charging', data),
  delete: (id) => api.delete(`/charging/${id}`),
};

// Sister Module API
export const sisterAPI = {
  getBills: () => api.get('/sister/bills'),
  createBill: (data) => api.post('/sister/bills', data),
  deleteBill: (id) => api.delete(`/sister/bills/${id}`),
  getSummary: (month) => api.get(`/sister/summary/${month}`),
  downloadPDF: (month) => api.get(`/sister/pdf/${month}`, { responseType: 'blob' }),
};

// Export API
export const exportAPI = {
  downloadCSV: () => api.get('/export/csv', { responseType: 'blob' }),
};

export default api;
