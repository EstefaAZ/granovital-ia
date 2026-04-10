// =============================================================
// frontend/src/services/authService.js
// Servicio de comunicación con la API de autenticación
// Trazabilidad: RF-01, RF-02 | RNF-04 (tokens en memoria)
// =============================================================

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

// Almacenamiento en memoria (más seguro que localStorage para tokens)
// El refresh token puede guardarse en una cookie HttpOnly en producción
let _accessToken = null;
let _nombreUsuario = "";
let _intentosFallidos = 0;
let _bloqueadoHasta = null;

const INTENTOS_MAX = 5;
const BLOQUEO_MS = 30000; // 30 segundos

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
    _nombreUsuario = "";
    sessionStorage.removeItem("gv_access");
    sessionStorage.removeItem("gv_refresh");
    // R-001 FIX: limpiar cultivo activo para que el siguiente usuario
    // no herede el cultivo del usuario anterior en el mismo tab
    sessionStorage.removeItem("gv_cultivo_id");
    sessionStorage.removeItem("gv_cultivo_nombre");
  },

  setNombreUsuario(nombre) {
    _nombreUsuario = nombre || "";
  },

  getNombreSanitizado() {
    const raw = _nombreUsuario || "Usuario";
    const limpio = raw.replace(/[\x00-\x1F\x7F]/g, "").trim();
    return limpio || "Usuario";
  },

  // ── Control de intentos fallidos / bloqueo ────────────────

  getIntentosFallidos() {
    if (this.estasBloqueado().bloqueado) {
      return INTENTOS_MAX;
    }
    return _intentosFallidos;
  },

  setIntentosFallidos(cantidad) {
    _intentosFallidos = Math.max(0, cantidad);
  },

  incrementarIntentosFallidos() {
    _intentosFallidos += 1;
    if (_intentosFallidos >= INTENTOS_MAX) {
      _bloqueadoHasta = Date.now() + BLOQUEO_MS;
    }
    return _intentosFallidos;
  },

  resetearIntentosFallidos() {
    _intentosFallidos = 0;
    _bloqueadoHasta = null;
  },

  estasBloqueado() {
    if (_bloqueadoHasta && Date.now() < _bloqueadoHasta) {
      return { bloqueado: true, msRestantes: _bloqueadoHasta - Date.now() };
    }
    _bloqueadoHasta = null;
    return { bloqueado: false, msRestantes: 0 };
  },

  // ── Login ─────────────────────────────────────────────────

  /**
   * Realiza el login contra POST /api/v1/auth/login
   * @param {string} correo
   * @param {string} contrasena
   * @returns {Promise<{usuario, access_token, refresh_token}>}
   */
  async login(correo, contrasena) {
    const bloqueo = this.estasBloqueado();
    if (bloqueo.bloqueado) {
      throw new ApiError(429, "Demasiados intentos fallidos. Intenta nuevamente más tarde.");
    }

    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ correo, contrasena }),
    });

    if (!response.ok) {
      this.incrementarIntentosFallidos();

      if (response.status === 401 || response.status === 403) {
        const error = await response.json();
        throw new ApiError(response.status, error.detail || "Error de autenticación");
      }

      if (response.status === 429) {
        throw new ApiError(429, "Demasiados intentos fallidos. Intenta nuevamente más tarde.");
      }

      const error = await response.json();
      throw new ApiError(response.status, error.detail || "Error de autenticación");
    }

    const data = await response.json();

    // Guardar access token en memoria
    _accessToken = data.access_token;
    this.setNombreUsuario(data.usuario?.nombre || "");
    // Refresh token en sessionStorage (se pierde al cerrar pestaña)
    sessionStorage.setItem("gv_refresh", data.refresh_token);

    this.resetearIntentosFallidos();
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
    const data = await response.json();
    this.setNombreUsuario(data.nombre || "");
    return data;
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

  // ── Registro ──────────────────────────────────────────────

  async registrar(datosRegistro) {
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datosRegistro),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new ApiError(response.status, error.detail || "Error en el registro");
    }

    const data = await response.json();

    // Guardar access token en memoria
    _accessToken = data.access_token;
    this.setNombreUsuario(data.usuario?.nombre || "");
    // Refresh token en sessionStorage
    sessionStorage.setItem("gv_refresh", data.refresh_token);

    return data;
  },

  // ── Enviar código de verificación ─────────────────────────

  async enviarCodigoVerificacion(correo) {
    const response = await fetch(`${API_BASE}/auth/send-verification-code`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ correo }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new ApiError(response.status, error.detail || "Error al enviar código");
    }

    return await response.json();
  },

  // ── Verificar estado del código ───────────────────────────

  async verificarEstadoCodigo(correo) {
    const response = await fetch(`${API_BASE}/auth/verify-code-status?correo=${encodeURIComponent(correo)}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new ApiError(response.status, error.detail || "Error al verificar estado");
    }

    return await response.json();
  },

  // ── Google OAuth ──────────────────────────────────────────

  async getGoogleAuthURL(state = null) {
    const params = state ? `?state=${encodeURIComponent(state)}` : "";
    const response = await fetch(`${API_BASE}/auth/google/auth-url${params}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new ApiError(response.status, error.detail || "Error al obtener URL de Google");
    }

    return await response.json();
  },

  async handleGoogleCallback(code, state = null) {
    const params = new URLSearchParams({ code });
    if (state) params.append("state", state);
    
    const response = await fetch(`${API_BASE}/auth/google/callback?${params}`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new ApiError(response.status, error.detail || "Error en autenticación con Google");
    }

    const data = await response.json();

    // Guardar access token en memoria
    _accessToken = data.access_token;
    this.setNombreUsuario(data.usuario?.nombre || "");
    // Refresh token en sessionStorage
    sessionStorage.setItem("gv_refresh", data.refresh_token);

    this.resetearIntentosFallidos();
    return data;
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
