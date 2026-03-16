// ==============================================================
// modulo_02_cultivos / frontend/src/services/cultivoService.js
// Cliente HTTP - Consumo de la API de Cultivos y Lotes
// RNF-01: timeout de 8 segundos por peticion
// RNF-04: adjunta el token JWT en cada solicitud
// ==============================================================

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

// Tiempo maximo de espera por peticion (RNF-01)
const TIMEOUT_MS = 8000;

/**
 * Realiza una peticion HTTP con autenticacion JWT automatica.
 * Lanza un error con el mensaje del servidor si la respuesta no es OK.
 */
async function peticion(ruta, opciones = {}) {
  const token = localStorage.getItem("access_token");

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
      throw new Error("La peticion supero el tiempo de espera (8 segundos)");
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

  /** Eliminacion logica de un cultivo. */
  eliminar: (id) =>
    peticion(`/cultivos/${id}`, { method: "DELETE" }),
};

// ==============================================================
// LOTES - RF-04
// ==============================================================

export const loteService = {
  /** Retorna los lotes de un cultivo. */
  listar: (cultivoId) => peticion(`/cultivos/${cultivoId}/lotes`),

  /** Retorna el detalle de un lote especifico. */
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

  /** Eliminacion logica de un lote. */
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
