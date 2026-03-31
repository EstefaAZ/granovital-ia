// ==============================================================
// modulo_04_ia / frontend/src/services/iaService.js
//
// OFF-003 FIX: timeout general aumentado a 20s para redes rurales
// IA-003  FIX: timeout separado de 45s para análisis de imagen ML
// ==============================================================

import { authService } from "./authService";

const API_BASE       = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
const TIMEOUT_MS     = 20_000; // OFF-003 FIX: 20s para peticiones normales
const TIMEOUT_IMG_MS = 45_000; // IA-003  FIX: 45s para inferencia ML + upload

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
      throw new Error("La conexión es lenta. Verifica tu señal e intenta de nuevo.");
    throw e;
  }
}

// IA-003 FIX: timeout de 45s exclusivo para upload + inferencia de imagen
async function peticionMultipart(ruta, formData, onProgress) {
  const token = authService.getAccessToken();

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}${ruta}`);
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    // IA-004 FIX: soporte de progreso de upload via XMLHttpRequest
    if (onProgress && xhr.upload) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          onProgress(Math.round((event.loaded / event.total) * 100));
        }
      };
    }

    // IA-003 FIX: timeout de 45s
    xhr.timeout = TIMEOUT_IMG_MS;
    xhr.ontimeout = () => {
      reject(new Error("El análisis tardó demasiado. Intenta con una imagen más pequeña."));
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(new Error("Respuesta inválida del servidor"));
        }
      } else {
        try {
          const err = JSON.parse(xhr.responseText);
          reject(new Error(err.detail || `Error ${xhr.status}`));
        } catch {
          reject(new Error(`Error ${xhr.status}`));
        }
      }
    };

    xhr.onerror = () => reject(new Error("Error de conexión al analizar la imagen."));
    xhr.send(formData);
  });
}

export const iaService = {
  resumen:   (cultivoId) => peticion(`/ia/${cultivoId}/resumen`),
  historial: (cultivoId, tipo, limite = 20) =>
    peticion(`/ia/${cultivoId}/historial?limite=${limite}${tipo ? `&tipo=${tipo}` : ""}`),

  // RF-05 — IA-004 FIX: acepta callback de progreso
  analizarEnfermedad: (cultivoId, archivo, onProgress) => {
    const fd = new FormData();
    fd.append("imagen", archivo);
    return peticionMultipart(`/ia/${cultivoId}/analisis/enfermedad`, fd, onProgress);
  },

  // RF-06 — IA-004 FIX: acepta callback de progreso
  analizarPlaga: (cultivoId, archivo, onProgress) => {
    const fd = new FormData();
    fd.append("imagen", archivo);
    return peticionMultipart(`/ia/${cultivoId}/analisis/plaga`, fd, onProgress);
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
