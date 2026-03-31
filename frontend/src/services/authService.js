// =============================================================
// frontend/src/services/authService.js
// Servicio de comunicación con la API de autenticación
// Trazabilidad: RF-01, RF-02 | RNF-04 (tokens en memoria)
//
// FIXES QA:
//   SEC-001: access token en variable de módulo JS (no en localStorage)
//   SEC-002: refresh token en sessionStorage expuesto a XSS
//            → NOTA: en producción mover a cookie HttpOnly desde el backend.
//              Mientras no se modifique el backend, se mantiene en sessionStorage
//              pero se documenta el riesgo y se agrega SameSite en la nota.
//   SEC-004: sin bloqueo tras múltiples intentos fallidos → implementado
//   AUTH-003: token expirado mid-session no redirige → manejado en refreshAccessToken
//   AUTH-004: logout no invalida token si access token es null → corregido
//   SEC-005: sanitización del nombre para el header HTTP
// =============================================================

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

// ── Almacenamiento en memoria (más seguro que localStorage) ──
// NOTA SEC-001: En producción, el backend debe emitir el access token
// como cookie HttpOnly + SameSite=Strict y eliminar este patrón.
let _accessToken = null;

// ── SEC-004: Protección contra fuerza bruta en el cliente ────
const INTENTOS_MAX = 5;
const BLOQUEO_MS   = 30_000; // 30 segundos
let _intentosFallidos = 0;
let _bloqueadoHasta   = null;

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
    // Limpiar también el bloqueo al hacer logout
    _intentosFallidos = 0;
    _bloqueadoHasta   = null;
  },

  // ── SEC-004: Estado de bloqueo por fuerza bruta ──────────

  estasBloqueado() {
    if (_bloqueadoHasta && Date.now() < _bloqueadoHasta) {
      return { bloqueado: true, msRestantes: _bloqueadoHasta - Date.now() };
    }
    if (_bloqueadoHasta && Date.now() >= _bloqueadoHasta) {
      // Bloqueo expiró, resetear contador
      _intentosFallidos = 0;
      _bloqueadoHasta   = null;
    }
    return { bloqueado: false, msRestantes: 0 };
  },

  getIntentosFallidos() {
    return _intentosFallidos;
  },

  // ── Login ─────────────────────────────────────────────────

  async login(correo, contrasena) {
    // SEC-004: verificar bloqueo antes de intentar
    const bloqueo = this.estasBloqueado();
    if (bloqueo.bloqueado) {
      const segs = Math.ceil(bloqueo.msRestantes / 1000);
      throw new ApiError(429,
        `Formulario bloqueado por múltiples intentos fallidos. Espera ${segs} segundos.`
      );
    }

    const response = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ correo, contrasena }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));

      // SEC-004: contar intentos fallidos (401 = credenciales incorrectas)
      if (response.status === 401 || response.status === 422) {
        _intentosFallidos += 1;
        if (_intentosFallidos >= INTENTOS_MAX) {
          _bloqueadoHasta = Date.now() + BLOQUEO_MS;
        }
      }

      throw new ApiError(response.status, error.detail || "Error de autenticación");
    }

    // Login exitoso → resetear contador
    _intentosFallidos = 0;
    _bloqueadoHasta   = null;

    const data = await response.json();

    // Guardar access token en memoria (no en localStorage)
    _accessToken = data.access_token;
    // SEC-002: Refresh token en sessionStorage. En producción usar cookie HttpOnly.
    sessionStorage.setItem("gv_refresh", data.refresh_token);

    return data;
  },

  // ── Logout ────────────────────────────────────────────────

  // AUTH-004 FIX: intentar invalidar el token aunque _accessToken sea null
  async logout() {
    const token = _accessToken;
    try {
      // Intentar refresh para obtener un token válido si el actual expiró
      const tokenValido = token || await this.refreshAccessToken().catch(() => null);
      if (tokenValido) {
        await fetch(`${API_BASE}/auth/logout`, {
          method: "POST",
          headers: { Authorization: `Bearer ${tokenValido}` },
        });
      }
    } catch {
      // Si falla el logout en el servidor, continuar limpiando tokens locales
    } finally {
      this.clearTokens();
    }
  },

  // ── Refresh token ─────────────────────────────────────────

  // AUTH-003 FIX: si el refresh falla, limpiar y señalizar para redirigir al login
  async refreshAccessToken() {
    const refreshToken = sessionStorage.getItem("gv_refresh");
    if (!refreshToken) {
      this.clearTokens();
      throw new ApiError(401, "No hay refresh token disponible. Inicia sesión nuevamente.");
    }

    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      this.clearTokens();
      throw new ApiError(401, "Sesión expirada. Por favor inicia sesión nuevamente.");
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
      const error = await response.json().catch(() => ({}));
      throw new ApiError(response.status, error.detail || "Error al cambiar contraseña");
    }
    return response.json();
  },

  // ── SEC-005: Nombre sanitizado para header HTTP ───────────
  getNombreSanitizado() {
    const nombre = sessionStorage.getItem("gv_nombre") || "Administrador";
    // Eliminar caracteres de control y saltos de línea que causan header injection
    return nombre.replace(/[\r\n\t\0]/g, "").substring(0, 100);
  },
};

// ── Clase de error personalizada ─────────────────────────────

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
    this.name   = "ApiError";
  }

  get esNoAutorizado()    { return this.status === 401; }
  get esAccesoDenegado()  { return this.status === 403; }
  get esDemasiados()      { return this.status === 429; }
}
