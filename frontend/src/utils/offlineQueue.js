// =============================================================
// frontend/src/utils/offlineQueue.js
// Cola offline para formularios de monitoreo ambiental y suelo
//
// OFF-002 FIX: datos ingresados offline se persisten en localStorage
//              y se sincronizan automáticamente al recuperar conexión.
// =============================================================

const CLAVE_AMBIENTAL = "gv_offline_ambiental";
const CLAVE_SUELO     = "gv_offline_suelo";

// ── Helpers de localStorage ───────────────────────────────────

function leer(clave) {
  try {
    return JSON.parse(localStorage.getItem(clave) || "[]");
  } catch {
    return [];
  }
}

function guardar(clave, datos) {
  try {
    localStorage.setItem(clave, JSON.stringify(datos));
  } catch {
    // localStorage puede no estar disponible (modo privado con cuota agotada)
    console.warn("offlineQueue: no se pudo guardar en localStorage");
  }
}

// ── API pública ───────────────────────────────────────────────

/**
 * Encola un registro ambiental para sincronizar cuando haya conexión.
 */
export function encolarAmbiental(cultivoId, payload) {
  const cola = leer(CLAVE_AMBIENTAL);
  cola.push({ cultivoId, payload, timestamp: Date.now() });
  guardar(CLAVE_AMBIENTAL, cola);
}

/**
 * Encola un registro de suelo para sincronizar cuando haya conexión.
 */
export function encolarSuelo(cultivoId, payload) {
  const cola = leer(CLAVE_SUELO);
  cola.push({ cultivoId, payload, timestamp: Date.now() });
  guardar(CLAVE_SUELO, cola);
}

/**
 * Retorna el número total de registros pendientes de sincronización.
 */
export function contarPendientes() {
  return leer(CLAVE_AMBIENTAL).length + leer(CLAVE_SUELO).length;
}

/**
 * Sincroniza todos los registros pendientes contra el servidor.
 * Requiere los servicios de monitoreo como parámetro para evitar
 * dependencias circulares.
 *
 * @param {{ ambientalService, sueloService }} servicios
 * @returns {{ sincronizados: number, fallidos: number }}
 */
export async function sincronizarPendientes({ ambientalService, sueloService }) {
  let sincronizados = 0;
  let fallidos      = 0;

  // ── Ambiental ───────────────────────────────────────────────
  const colaAmb = leer(CLAVE_AMBIENTAL);
  const pendienteAmb = [];
  for (const item of colaAmb) {
    try {
      await ambientalService.registrar(item.cultivoId, item.payload);
      sincronizados++;
    } catch {
      // Mantener en la cola para reintento posterior
      pendienteAmb.push(item);
      fallidos++;
    }
  }
  guardar(CLAVE_AMBIENTAL, pendienteAmb);

  // ── Suelo ───────────────────────────────────────────────────
  const colaSue = leer(CLAVE_SUELO);
  const pendienteSue = [];
  for (const item of colaSue) {
    try {
      await sueloService.registrar(item.cultivoId, item.payload);
      sincronizados++;
    } catch {
      pendienteSue.push(item);
      fallidos++;
    }
  }
  guardar(CLAVE_SUELO, pendienteSue);

  return { sincronizados, fallidos };
}

/**
 * Limpia toda la cola pendiente (usar solo en casos de reset manual).
 */
export function limpiarCola() {
  localStorage.removeItem(CLAVE_AMBIENTAL);
  localStorage.removeItem(CLAVE_SUELO);
}
