// ==============================================================
// modulo_06_mercado / frontend/src/services/mercadoService.js
// ==============================================================

import { authService } from "./authService";

const API_BASE   = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
const TIMEOUT_MS = 8000;

async function peticion(ruta, opciones = {}) {
  const token = authService.getAccessToken();
  const ctrl  = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${API_BASE}${ruta}`, {
      ...opciones,
      signal:  ctrl.signal,
      headers: {
        "Content-Type": "application/json",
        Authorization:  token ? `Bearer ${token}` : "",
        ...(opciones.headers || {}),
      },
    });
    clearTimeout(timer);
    if (!res.ok) {
      const e = await res.json().catch(() => ({}));
      throw new Error(e.detail || `Error ${res.status}`);
    }
    return res.status === 204 ? null : res.json();
  } catch (e) {
    clearTimeout(timer);
    if (e.name === "AbortError") throw new Error("Tiempo de espera agotado.");
    throw e;
  }
}

export const mercadoService = {
  dashboard:          ()             => peticion("/mercado/dashboard"),
  registrarPrecio:    (datos)        => peticion("/mercado/precios", { method: "POST", body: JSON.stringify(datos) }),
  listarPrecios:      (fuente, meses) => peticion(`/mercado/precios?${fuente ? `fuente=${fuente}&` : ""}meses=${meses || 6}`),
  sincronizar:        ()             => peticion("/mercado/precios/sincronizar", { method: "POST" }),
  historialPrecios:   (meses, tipo)  => peticion(`/mercado/precios/historial?meses=${meses || 6}&tipo_cafe=${tipo || "pergamino_seco"}`),
  analizarPrecios:    (params)       => peticion(`/mercado/precios/analisis?meses=${params.meses||6}&tipo_cafe=${params.tipo||"pergamino_seco"}&fuente_filtro=${params.fuente||"todas"}`, { method: "POST" }),
  analizarDemanda:    (meses, obs)   => peticion(`/mercado/demanda/analisis?meses=${meses||6}`, { method: "POST", body: obs ? JSON.stringify(obs) : undefined }),
};
