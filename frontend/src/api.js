import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const getWsUrl = () => {
  return API_BASE.replace(/^http/, 'ws') + '/ws/progress';
};

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('qflow_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth
export const register = (data) => api.post('/auth/register', data);
export const login = (data) => api.post('/auth/login', data);
export const getMe = () => api.get('/auth/me');

// Strategies
export const getStrategyTypes = () => api.get('/strategies/types');
export const createStrategy = (data) => api.post('/strategies/', data);
export const getStrategies = () => api.get('/strategies/');
export const getStrategy = (id) => api.get(`/strategies/${id}`);
export const deleteStrategy = (id) => api.delete(`/strategies/${id}`);

// Backtests
export const submitBacktest = (data) => api.post('/backtests/', data);
export const getBacktests = (params) => api.get('/backtests/', { params });
export const getBacktest = (id) => api.get(`/backtests/${id}`);
export const getEquityCurve = (id) => api.get(`/backtests/${id}/equity`);
export const getTrades = (id) => api.get(`/backtests/${id}/trades`);
export const getAnalytics = (id) => api.get(`/backtests/${id}/analytics`);

// Market Data
export const getSymbols = () => api.get('/market-data/symbols');
export const getMarketData = (symbol, params) => api.get(`/market-data/${symbol}`, { params });

export default api;
