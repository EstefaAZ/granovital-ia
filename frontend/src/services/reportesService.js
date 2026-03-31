// ==============================================================
// modulo_07_reportes / frontend/src/services/reportesService.js
//
// SEC-005 FIX: nombre sanitizado para header X-Usuario-Nombre
// REP-001 FIX: descarga de reporte con appendChild/removeChild correcto
// ==============================================================

import { authService } from "./authService";

const API_BASE   = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
const TIMEOUT_MS = 10_000; // 10s — la generación puede tardar un poco más

async function peticion(ruta, opciones = {}) {
  const token = authService.getAccessToken();
  // SEC-005 FIX: usar el método sanitizado que elimina caracteres de control
  const nombre = authService.getNombreSanitizado();
  const ctrl  = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${API_BASE}${ruta}`, {
      ...opciones,
      signal: ctrl.signal,
      headers: {
        "Content-Type":     "application/json",
        Authorization:      token ? `Bearer ${token}` : "",
        // SEC-005 FIX: encodeURIComponent por si el nombre tiene caracteres especiales
        "X-Usuario-Nombre": encodeURIComponent(nombre),
        ...(opciones.headers || {}),
      },
    });
    clearTimeout(timer);
    if (!res.ok) {
      const e = await res.json().catch(() => ({}));
      throw new Error(e.detail || `Error ${res.status}`);
    }
    // Para descarga de archivos
    if (opciones._blob) return res.blob();
    return res.status === 204 ? null : res.json();
  } catch (e) {
    clearTimeout(timer);
    if (e.name === "AbortError") throw new Error("Tiempo de espera agotado.");
    throw e;
  }
}

// REP-001 FIX: helper de descarga segura con appendChild/removeChild
export function descargarBlob(blob, nombreArchivo) {
  const url = URL.createObjectURL(blob);
  const a   = document.createElement("a");
  a.href     = url;
  a.download = nombreArchivo;
  // REP-001 FIX: agregar al DOM antes de .click() (necesario en Safari)
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  // Liberar la URL de objeto para evitar memory leaks
  URL.revokeObjectURL(url);
}

export const reportesService = {
  resumenSistema:    ()       => peticion("/reportes/resumen"),
  solicitarReporte:  (datos)  => peticion("/reportes", { method: "POST", body: JSON.stringify(datos) }),
  listarReportes:    ()       => peticion("/reportes"),
  obtenerReporte:    (id)     => peticion(`/reportes/${id}`),
  reintentarReporte: (id)     => peticion(`/reportes/${id}/reintentar`, { method: "POST" }),

  // REP-001 FIX: retorna el blob; la llamada a descargarBlob queda en la UI
  descargarReporte:  (id)     => peticion(`/reportes/${id}/descargar`, { _blob: true }),

  consultarAuditoria: (params) => peticion(
    `/auditoria?${new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v != null))
    )}`
  ),
  registrarAuditoria: (evento) =>
    peticion("/auditoria", { method: "POST", body: JSON.stringify(evento) }),
};
