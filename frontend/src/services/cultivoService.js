// ==============================================================
// modulo_02_cultivos / frontend/src/services/cultivoService.js
// Cliente HTTP — Consumo de la API de Cultivos y Lotes
// RNF-01: timeout por petición
// RNF-04: adjunta el token JWT en cada solicitud
//
// OFF-003 FIX: timeout aumentado a 20s para conexiones 2G/Edge en campo
// ==============================================================

import { authService } from "./authService";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

// OFF-003 FIX: 20 segundos para redes rurales lentas (original era 8s)
const TIMEOUT_MS = 20_000;

/**
 * Realiza una petición HTTP con autenticación JWT automática.
 * Lanza un error con el mensaje del servidor si la respuesta no es OK.
 */
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
// CULTIVOS - RF-03
// ==============================================================

export const cultivoService = {
  /** Obtiene el resumen del dashboard del caficultor. */
  resumen: () => peticion("/cultivos/resumen"),

  /** Retorna la lista de cultivos del usuario autenticado. */
  listar: () => peticion("/cultivos"),

  /** Retorna el detalle de un cultivo por su ID. */
  obtener: (id) => peticion(`/cultivos/${id}`),

  /** Crea un nuevo cultivo. */
  crear: (datos) =>
    peticion("/cultivos", {
      method: "POST",
      body: JSON.stringify(datos),
    }),

  /** Actualiza parcialmente un cultivo. */
  actualizar: (id, datos) =>
    peticion(`/cultivos/${id}`, {
      method: "PATCH",
      body: JSON.stringify(datos),
    }),

  /** Eliminación lógica de un cultivo. */
  eliminar: (id) =>
    peticion(`/cultivos/${id}`, { method: "DELETE" }),
};

// ==============================================================
// LOTES - RF-04
// ==============================================================

export const loteService = {
  /** Retorna los lotes de un cultivo. */
  listar: (cultivoId) => peticion(`/cultivos/${cultivoId}/lotes`),

  /** Retorna el detalle de un lote específico. */
  obtener: (cultivoId, loteId) =>
    peticion(`/cultivos/${cultivoId}/lotes/${loteId}`),

  /** Registra un nuevo lote en el cultivo. */
  crear: (cultivoId, datos) =>
    peticion(`/cultivos/${cultivoId}/lotes`, {
      method: "POST",
      body: JSON.stringify(datos),
    }),

  /** Actualiza el estado u observaciones de un lote. */
  actualizar: (cultivoId, loteId, datos) =>
    peticion(`/cultivos/${cultivoId}/lotes/${loteId}`, {
      method: "PATCH",
      body: JSON.stringify(datos),
    }),

  /** Eliminación lógica de un lote. */
  eliminar: (cultivoId, loteId) =>
    peticion(`/cultivos/${cultivoId}/lotes/${loteId}`, { method: "DELETE" }),
};

// ==============================================================
// SENSORES - RNF-06
// ==============================================================

export const sensorService = {
  /** Retorna los sensores registrados en un cultivo. */
  listar: (cultivoId) => peticion(`/cultivos/${cultivoId}/sensores`),

  /** Registra un nuevo sensor IoT (solo Administrador). */
  registrar: (cultivoId, datos) =>
    peticion(`/cultivos/${cultivoId}/sensores`, {
      method: "POST",
      body: JSON.stringify(datos),
    }),
};
