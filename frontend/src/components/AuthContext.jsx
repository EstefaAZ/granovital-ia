// =============================================================
// frontend/src/components/AuthContext.jsx
// Contexto global de autenticación — React Context API
// Trazabilidad: RF-01, RF-02 | RN-01 (acceso por rol)
// =============================================================

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { authService } from "../services/authService";

const AuthContext = createContext(null);

/**
 * Proveedor de autenticación global.
 * Envuelve toda la aplicación para que cualquier componente
 * pueda acceder al usuario, rol y funciones de login/logout.
 */
export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

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
        // Sin sesión activa — estado inicial sin usuario
        authService.clearTokens();
      } finally {
        setCargando(false);
      }
    };
    restaurarSesion();
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

  const esAdmin        = () => tieneRol("Administrador");
  const esCaficultor   = () => tieneRol("Caficultor", "Administrador");
  const esProductor    = () => tieneRol("Productor", "Administrador");
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

/** Hook de conveniencia para usar el contexto de auth. */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
