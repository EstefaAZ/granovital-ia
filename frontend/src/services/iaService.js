// ==============================================================
// modulo_04_ia / frontend/src/services/iaService.js
// Cliente HTTP - Modulo de Inteligencia Artificial
// RNF-01: timeout de 8 segundos (5s inferencia + margen)
// ==============================================================

import { authService } from "./authService";

const API_BASE   = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
const TIMEOUT_MS = 8000;

async function peticion(ruta, opciones = {}) {
  const token = authService.getAccessToken();
  const controller = new AbortController();
  const timer      = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${API_BASE}${ruta}`, {
      ...opciones,
      signal:  controller.signal,
      headers: {
        Authorization: token ? `Bearer ${token}` : "",
        ...(opciones.headers || {}),
      },
    });
    clearTimeout(timer);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Error ${res.status}`);
    }
    return res.status === 204 ? null : res.json();
  } catch (e) {
    clearTimeout(timer);
    if (e.name === "AbortError")
      throw new Error("La peticion supero el tiempo permitido. Intente de nuevo.");
    throw e;
  }
}

async function peticionMultipart(ruta, formData) {
  const token = authService.getAccessToken();
  const controller = new AbortController();
  const timer      = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${API_BASE}${ruta}`, {
      method:  "POST",
      signal:  controller.signal,
      headers: { Authorization: token ? `Bearer ${token}` : "" },
      body:    formData,
    });
    clearTimeout(timer);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Error ${res.status}`);
    }
    return res.json();
  } catch (e) {
    clearTimeout(timer);
    if (e.name === "AbortError")
      throw new Error("El analisis tardo demasiado. Intente con una imagen mas pequena.");
    throw e;
  }
}

export const iaService = {
  resumen:    (cultivoId) => peticion(`/ia/${cultivoId}/resumen`),
  historial:  (cultivoId, tipo, limite = 20) =>
    peticion(`/ia/${cultivoId}/historial?limite=${limite}${tipo ? `&tipo=${tipo}` : ""}`),

  // RF-05
  analizarEnfermedad: (cultivoId, archivo) => {
    const fd = new FormData();
    fd.append("imagen", archivo);
    return peticionMultipart(`/ia/${cultivoId}/analisis/enfermedad`, fd);
  },

  // RF-06
  analizarPlaga: (cultivoId, archivo) => {
    const fd = new FormData();
    fd.append("imagen", archivo);
    return peticionMultipart(`/ia/${cultivoId}/analisis/plaga`, fd);
  },

  // RF-07
  predecirFitosanitario: (cultivoId) =>
    peticion(`/ia/${cultivoId}/prediccion/fitosanitaria`, { method: "POST" }),

  // RF-08
  recomendarRiego: (cultivoId) =>
    peticion(`/ia/${cultivoId}/recomendacion/riego`, { method: "POST" }),

  // RF-09
  recomendarFertilizacion: (cultivoId) =>
    peticion(`/ia/${cultivoId}/recomendacion/fertilizacion`, { method: "POST" }),

  // RNF-08
  recargarModelo: (tipo) =>
    peticion(`/ia/admin/modelos/${tipo}/reload`, { method: "POST" }),
};
