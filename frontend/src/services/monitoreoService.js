// ==============================================================
// modulo_03_monitoreo / frontend/src/services/monitoreoService.js
// Cliente HTTP — Consumo de la API de Monitoreo
// RNF-01: timeout por petición
// RNF-04: token JWT adjunto automáticamente
//
// OFF-003 FIX: timeout aumentado a 20s para conexiones 2G/Edge en campo
// ==============================================================

import { authService } from "./authService";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

// OFF-003 FIX: 20 segundos para redes rurales (original era 8s)
const TIMEOUT_MS = 20_000;

async function peticion(ruta, opciones = {}) {
  const token = authService.getAccessToken();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const respuesta = await fetch(`${API_BASE}${ruta}`, {
      ...opciones,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        Authorization: token ? `Bearer ${token}` : "",
        ...(opciones.headers || {}),
      },
    });
    clearTimeout(timer);
    if (!respuesta.ok) {
      const error = await respuesta.json().catch(() => ({}));
      throw new Error(error.detail || `Error ${respuesta.status}`);
    }
    if (respuesta.status === 204) return null;
    return respuesta.json();
  } catch (err) {
    clearTimeout(timer);
    if (err.name === "AbortError") {
      throw new Error("La conexión es lenta. Verifica tu señal e intenta de nuevo.");
    }
    throw err;
  }
}

// ==============================================================
// RESUMEN Y VALIDEZ
// ==============================================================

export const monitoreoService = {
  /** Resumen consolidado del monitoreo del cultivo. */
  resumen: (cultivoId) => peticion(`/monitoreo/${cultivoId}/resumen`),

  /** RN-03: verifica si los datos están dentro del umbral de 24 horas. */
  verificarValidez: (cultivoId) => peticion(`/monitoreo/${cultivoId}/validez`),
};

// ==============================================================
// AMBIENTAL - RF-03
// ==============================================================

export const ambientalService = {
  registrar: (cultivoId, datos) =>
    peticion(`/monitoreo/${cultivoId}/ambiental`, {
      method: "POST",
      body:   JSON.stringify(datos),
    }),

  listar: (cultivoId, limite = 50) =>
    peticion(`/monitoreo/${cultivoId}/ambiental?limite=${limite}`),

  ultima: (cultivoId) =>
    peticion(`/monitoreo/${cultivoId}/ambiental/ultima`),
};

// ==============================================================
// SUELO - RF-04
// ==============================================================

export const sueloService = {
  registrar: (cultivoId, datos) =>
    peticion(`/monitoreo/${cultivoId}/suelo`, {
      method: "POST",
      body:   JSON.stringify(datos),
    }),

  listar: (cultivoId, limite = 50) =>
    peticion(`/monitoreo/${cultivoId}/suelo?limite=${limite}`),

  ultima: (cultivoId) =>
    peticion(`/monitoreo/${cultivoId}/suelo/ultima`),
};
