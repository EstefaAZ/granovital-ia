// ==============================================================
// modulo_03_monitoreo / frontend/src/hooks/useMonitoreo.js
// Hook React para estado y logica del monitoreo
// Encapsula carga de datos, polling automatico y alertas
// ==============================================================

import { useState, useEffect, useCallback, useRef } from "react";  // BUG-049 FIX
import {
  monitoreoService,
  ambientalService,
  sueloService,
} from "../services/monitoreoService";

/**
 * Hook principal de monitoreo.
 * Carga el resumen, las ultimas lecturas y la validez RN-03.
 * Realiza polling cada 'intervaloSegundos' para actualizacion automatica.
 */
export function useMonitoreo(cultivoId, intervaloSegundos = 60) {
  const [resumen,   setResumen]   = useState(null);
  const [validez,   setValidez]   = useState(null);
  const [cargando,  setCargando]  = useState(true);
  const [error,     setError]     = useState("");

  const cargar = useCallback(async () => {
    if (!cultivoId) return;
    setCargando(true);
    setError("");
    try {
      const [res, val] = await Promise.all([
        monitoreoService.resumen(cultivoId),
        monitoreoService.verificarValidez(cultivoId),
      ]);
      setResumen(res);
      setValidez(val);
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }, [cultivoId]);

  // BUG-049 FIX: useRef garantiza que solo hay un intervalo activo a la vez
  const intervaloRef = useRef(null);
  useEffect(() => {
    cargar();
    if (intervaloRef.current) clearInterval(intervaloRef.current);
    intervaloRef.current = setInterval(cargar, intervaloSegundos * 1000);
    return () => {
      if (intervaloRef.current) clearInterval(intervaloRef.current);
    };
  }, [cargar, intervaloSegundos]);

  return { resumen, validez, cargando, error, recargar: cargar };
}

/**
 * Hook para el historial de lecturas ambientales.
 */
export function useHistorialAmbiental(cultivoId, limite = 20) {
  const [historial, setHistorial] = useState([]);
  const [cargando,  setCargando]  = useState(false);

  const cargar = useCallback(async () => {
    if (!cultivoId) return;
    setCargando(true);
    try {
      const datos = await ambientalService.listar(cultivoId, limite);
      setHistorial(datos || []);
    } catch (_) {
      setHistorial([]);
    } finally {
      setCargando(false);
    }
  }, [cultivoId, limite]);

  useEffect(() => { cargar(); }, [cargar]);

  return { historial, cargando, recargar: cargar };
}

/**
 * Hook para el historial de lecturas de suelo.
 */
export function useHistorialSuelo(cultivoId, limite = 20) {
  const [historial, setHistorial] = useState([]);
  const [cargando,  setCargando]  = useState(false);

  const cargar = useCallback(async () => {
    if (!cultivoId) return;
    setCargando(true);
    try {
      const datos = await sueloService.listar(cultivoId, limite);
      setHistorial(datos || []);
    } catch (_) {
      setHistorial([]);
    } finally {
      setCargando(false);
    }
  }, [cultivoId, limite]);

  useEffect(() => { cargar(); }, [cargar]);

  return { historial, cargando, recargar: cargar };
}
