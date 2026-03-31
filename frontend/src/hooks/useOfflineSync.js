// =============================================================
// frontend/src/hooks/useOfflineSync.js
// Hook que sincroniza la cola offline cuando se recupera la red
//
// OFF-002 FIX: sincronización automática al volver a estar online
// =============================================================

import { useEffect, useState } from "react";
import { sincronizarPendientes, contarPendientes } from "../utils/offlineQueue";
import { ambientalService, sueloService } from "../services/monitoreoService";

/**
 * Se usa en el componente raíz (App.jsx o Layout.jsx) para activar
 * la sincronización automática de registros pendientes en background.
 */
export function useOfflineSync() {
  const [pendientes,    setPendientes]    = useState(contarPendientes());
  const [sincronizando, setSincronizando] = useState(false);
  const [ultimoResultado, setUltimoResultado] = useState(null);

  const sincronizar = async () => {
    const total = contarPendientes();
    if (total === 0 || sincronizando) return;

    setSincronizando(true);
    try {
      const resultado = await sincronizarPendientes({ ambientalService, sueloService });
      setPendientes(contarPendientes());
      setUltimoResultado(resultado);
    } catch {
      // Silencioso — se reintentará en el próximo evento online
    } finally {
      setSincronizando(false);
    }
  };

  useEffect(() => {
    // Sincronizar al recuperar la conexión
    const alVolver = () => {
      setPendientes(contarPendientes());
      sincronizar();
    };

    window.addEventListener("online", alVolver);

    // También intentar al montar (por si había pendientes de sesiones anteriores)
    if (navigator.onLine) {
      sincronizar();
    } else {
      setPendientes(contarPendientes());
    }

    return () => window.removeEventListener("online", alVolver);
  }, []); // eslint-disable-line

  return { pendientes, sincronizando, ultimoResultado };
}
