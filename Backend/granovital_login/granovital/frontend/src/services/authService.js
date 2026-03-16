// =============================================================
// frontend/src/services/authService.js
// Servicio de comunicación con la API de autenticación
// Trazabilidad: RF-01, RF-02 | RNF-04 (tokens en memoria)
// =============================================================

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000/api/v1";

// Almacenamiento en memoria (más seguro que localStorage para tokens)
// El refresh token puede guardarse en una cookie HttpOnly en producción
let _accessToken = null;

export const authService = {
  // ── Getters / Setters de token ────────────────────────────

  setAccessToken(token) {
    _accessToken = token;
  },

  getAccessToken() {
    return _accessToken;
  },

  clearTokens() {
    _accessToken = null;
    sessionStorage.removeItem("gv_refresh");
  },

  // ── Login ─────────────────────────────────────────────────

  /**
   * Realiza el login contra POST /api/v1/auth/login
   * @param {string} correo
   * @param {string} contrasena
   * @returns {Promise<{usuario, access_token, refresh_token}>}
   */
  async login(correo, contrasena) {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ correo, contrasena }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new ApiError(response.status, error.detail || "Error de autenticación");
    }

    const data = await response.json();

    // Guardar access token en memoria
    _accessToken = data.access_token;
    // Refresh token en sessionStorage (se pierde al cerrar pestaña)
    sessionStorage.setItem("gv_refresh", data.refresh_token);

    return data;
  },

  // ── Logout ────────────────────────────────────────────────

  async logout() {
    try {
      if (_accessToken) {
        await fetch(`${API_BASE}/auth/logout`, {
          method: "POST",
          headers: { Authorization: `Bearer ${_accessToken}` },
        });
      }
    } finally {
      this.clearTokens();
    }
  },

  // ── Refresh token ─────────────────────────────────────────

  async refreshAccessToken() {
    const refreshToken = sessionStorage.getItem("gv_refresh");
    if (!refreshToken) throw new Error("No hay refresh token disponible");

    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      this.clearTokens();
      throw new ApiError(401, "Sesión expirada, por favor inicia sesión nuevamente");
    }

    const data = await response.json();
    _accessToken = data.access_token;
    return data.access_token;
  },

  // ── Verificar sesión activa ───────────────────────────────

  async getMe() {
    const token = _accessToken || (await this.refreshAccessToken());
    const response = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new ApiError(response.status, "Sesión inválida");
    return response.json();
  },

  // ── Cambio de contraseña ──────────────────────────────────

  async cambiarPassword(contrasena_actual, contrasena_nueva, contrasena_nueva_confirmar) {
    const response = await fetch(`${API_BASE}/auth/change-password`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${_accessToken}`,
      },
      body: JSON.stringify({ contrasena_actual, contrasena_nueva, contrasena_nueva_confirmar }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new ApiError(response.status, error.detail || "Error al cambiar contraseña");
    }
    return response.json();
  },
};

// ── Clase de error personalizada ─────────────────────────────

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }

  get esNoAutorizado() { return this.status === 401; }
  get esAccesoDenegado() { return this.status === 403; }
  get esDemasiados() { return this.status === 429; }
}
