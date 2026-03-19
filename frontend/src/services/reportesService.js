// ==============================================================
// modulo_07_reportes / frontend/src/services/reportesService.js
// ==============================================================

const API_BASE   = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
const TIMEOUT_MS = 10000;  // 10s — la generación puede tardar un poco más

async function peticion(ruta, opciones = {}) {
  const token = localStorage.getItem("access_token");
  const nombre = localStorage.getItem("nombre_usuario") || "Administrador";
  const ctrl  = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${API_BASE}${ruta}`, {
      ...opciones,
      signal: ctrl.signal,
      headers: {
        "Content-Type":   "application/json",
        Authorization:    token ? `Bearer ${token}` : "",
        "X-Usuario-Nombre": nombre,
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

export const reportesService = {
  resumenSistema:   ()           => peticion("/reportes/resumen"),
  solicitarReporte: (datos)      => peticion("/reportes", { method: "POST", body: JSON.stringify(datos) }),
  listarReportes:   ()           => peticion("/reportes"),
  obtenerReporte:   (id)         => peticion(`/reportes/${id}`),
  descargarReporte: (id)         => peticion(`/reportes/${id}/descargar`, { _blob: true }),
  reintentarReporte:(id)         => peticion(`/reportes/${id}/reintentar`, { method: "POST" }),
  consultarAuditoria: (params)   => peticion(`/auditoria?${new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([,v]) => v != null))
  )}`),
  registrarAuditoria: (evento)   => peticion("/auditoria", { method: "POST", body: JSON.stringify(evento) }),
};
