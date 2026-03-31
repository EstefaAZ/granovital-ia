// =============================================================
// frontend/src/components/AuthContext.jsx
//
// AUTH-003 FIX: token expirado mid-session redirige al login
//               Se escucha el evento 'gv:session_expired' emitido
//               por api.js cuando el refresh falla.
// =============================================================

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { authService } from "../services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [usuario,  setUsuario]  = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error,    setError]    = useState(null);

  // ── Verificar sesión al cargar la app ──────────────────────
  useEffect(() => {
    const restaurarSesion = async () => {
      try {
        const refreshToken = sessionStorage.getItem("gv_refresh");
        if (refreshToken) {
          const me = await authService.getMe();
          setUsuario(me);
        }
      } catch {
        authService.clearTokens();
      } finally {
        setCargando(false);
      }
    };
    restaurarSesion();
  }, []);

  // AUTH-003 FIX: escuchar evento de sesión expirada mid-session
  // api.js emite este evento cuando el refresh token también falla
  useEffect(() => {
    const manejarSesionExpirada = () => {
      authService.clearTokens();
      setUsuario(null);
      // La redirección la maneja el RutaProtegida en App.jsx
      // al detectar estaAutenticado === false
    };

    window.addEventListener("gv:session_expired", manejarSesionExpirada);
    return () => window.removeEventListener("gv:session_expired", manejarSesionExpirada);
  }, []);

  // ── Login ───────────────────────────────────────────────────
  const login = useCallback(async (correo, contrasena) => {
    setError(null);
    const data = await authService.login(correo, contrasena);
    setUsuario(data.usuario);
    return data;
  }, []);

  // ── Logout ──────────────────────────────────────────────────
  const logout = useCallback(async () => {
    await authService.logout();
    setUsuario(null);
  }, []);

  // ── Helpers de rol (RN-01) ──────────────────────────────────
  const tieneRol = useCallback(
    (...roles) => usuario && roles.includes(usuario.rol?.nombre_rol),
    [usuario]
  );

  const esAdmin           = () => tieneRol("Administrador");
  const esCaficultor      = () => tieneRol("Caficultor", "Administrador");
  const esProductor       = () => tieneRol("Productor", "Administrador");
  const esComercializador = () => tieneRol("Comercializador", "Administrador");

  const valor = {
    usuario,
    cargando,
    error,
    setError,
    estaAutenticado: !!usuario,
    login,
    logout,
    tieneRol,
    esAdmin,
    esCaficultor,
    esProductor,
    esComercializador,
  };

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
