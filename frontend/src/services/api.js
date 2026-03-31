// =============================================================
// frontend/src/services/api.js
// Cliente HTTP base con Axios
//
// SEC-003 FIX: unificado el origen del token. Ya no se lee de
// localStorage('token') — ahora siempre usa authService.getAccessToken()
// que mantiene el token en memoria, consistente con authService.js.
// =============================================================
import axios from 'axios';
import { authService } from './authService';

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
});

// Agrega el token JWT a cada petición automáticamente desde authService
API.interceptors.request.use((config) => {
  // SEC-003 FIX: leer SIEMPRE desde authService (memoria), nunca desde localStorage
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
        // AUTH-003 FIX: limpiar tokens y emitir evento para que AuthContext
        // detecte la sesión expirada y el estado React se actualice limpiamente
        authService.clearTokens();
        window.dispatchEvent(new CustomEvent("gv:session_expired"));
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default API;
