// =============================================================
// frontend/src/services/api.js
// Cliente HTTP base — BUG-005 FIX
// El token se lee desde authService (memoria/sessionStorage),
// NO desde localStorage (era inconsistente con authService.js)
// =============================================================
import axios from 'axios';
import { authService } from './authService';

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
});

// Agrega el token JWT a cada petición automáticamente desde authService
API.interceptors.request.use((config) => {
  // BUG-005 FIX: leer desde authService, no localStorage
  const token = authService.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Si el token expira, intenta refresh automático; si falla, redirige al login
API.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const newToken = await authService.refreshAccessToken();
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return API(originalRequest);
      } catch (_) {
        authService.clearTokens();
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default API;