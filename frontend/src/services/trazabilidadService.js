// ==============================================================
// modulo_05_trazabilidad / frontend/src/services/trazabilidadService.js
// Cliente HTTP — Modulo de Trazabilidad
// ==============================================================

const API_BASE   = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
const TIMEOUT_MS = 8000;

async function peticion(ruta, opciones = {}) {
  const token      = localStorage.getItem("access_token");
  const controller = new AbortController();
  const timer      = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(`${API_BASE}${ruta}`, {
      ...opciones,
      signal:  controller.signal,
      headers: {
        "Content-Type": "application/json",
        Authorization:  token ? `Bearer ${token}` : "",
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
      throw new Error("La peticion supero el tiempo limite. Intente de nuevo.");
    throw e;
  }
}

export const trazabilidadService = {
  // RF-10 — Lotes
  crearLote:      (datos)       => peticion("/trazabilidad/lotes", { method: "POST", body: JSON.stringify(datos) }),
  listarLotes:    (cultivoId)   => peticion(`/trazabilidad/lotes${cultivoId ? `?cultivo_id=${cultivoId}` : ""}`),
  obtenerLote:    (id)          => peticion(`/trazabilidad/lotes/${id}`),
  actualizarLote: (id, datos)   => peticion(`/trazabilidad/lotes/${id}`, { method: "PATCH", body: JSON.stringify(datos) }),
  confirmarLote:  (id)          => peticion(`/trazabilidad/lotes/${id}/confirmar`, { method: "POST" }),
  registrarVenta: (id, p)       => peticion(
    `/trazabilidad/lotes/${id}/venta?comprador=${encodeURIComponent(p.comprador)}&precio_kg=${p.precio_kg}${p.destino ? `&destino=${encodeURIComponent(p.destino)}` : ""}`,
    { method: "POST" }
  ),
  logEventos:     (id)          => peticion(`/trazabilidad/lotes/${id}/eventos`),

  // RF-11 — Secado
  registrarSecado:  (idLote, datos) => peticion(`/trazabilidad/lotes/${idLote}/secado`, { method: "POST", body: JSON.stringify(datos) }),
  resumenSecado:    (idLote)        => peticion(`/trazabilidad/lotes/${idLote}/secado/resumen`),

  // RF-12 — Clasificacion
  clasificarGrano:  (idLote, datos) => peticion(`/trazabilidad/lotes/${idLote}/clasificacion`, { method: "POST", body: JSON.stringify(datos) }),

  // RF-15 / RN-05 — Consulta publica (sin token)
  consultaPublica: (codigoLote) => fetch(`${API_BASE}/trazabilidad/publico/${codigoLote}`).then(r => r.json()),
};
