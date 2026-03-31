// ==============================================================
// frontend/src/components/FormularioAmbiental.jsx
//
// DATA-001 FIX: validación de 'al menos un campo numérico' antes de submit
// DATA-003 FIX: botón deshabilitado tras primer submit hasta respuesta del servidor
// ==============================================================

import { useState, useRef } from "react";
import { ambientalService } from "../services/monitoreoService";
import { encolarAmbiental, sincronizarPendientes, contarPendientes } from "../utils/offlineQueue";

const COLOR = {
  cafe:   "#6f3a1b",
  borde:  "#d4b896",
  fondo:  "#f9f3ee",
  verde:  "#2d7a3a",
  rojo:   "#b91c1c",
};

// Rangos válidos por variable
const RANGOS = {
  temperatura:      { min: -10, max: 55,   label: "Temperatura (°C)"         },
  humedad_relativa: { min: 0,   max: 100,  label: "Humedad relativa (%)"     },
  precipitacion_mm: { min: 0,   max: 2000, label: "Precipitación (mm)"       },
  radiacion_solar:  { min: 0,   max: 2000, label: "Radiación solar (W/m²)"   },
  velocidad_viento: { min: 0,   max: 300,  label: "Velocidad viento (km/h)"  },
};

function Campo({ label, name, value, onChange, placeholder = "", ayuda = "", errorMsg = "" }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
      <label style={{ fontSize: "0.82rem", fontWeight: 600, color: "#4a2c0a" }}>
        {label}
      </label>
      <input
        name={name}
        type="number"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        step="0.01"
        style={{
          padding:      "0.55rem 0.85rem",
          border:       `1.5px solid ${errorMsg ? COLOR.rojo : COLOR.borde}`,
          borderRadius: "8px",
          fontSize:     "0.9rem",
          outline:      "none",
        }}
      />
      {ayuda && !errorMsg && (
        <span style={{ fontSize: "0.73rem", color: "#9a7a5a" }}>{ayuda}</span>
      )}
      {errorMsg && (
        <span style={{ fontSize: "0.73rem", color: COLOR.rojo }} role="alert">{errorMsg}</span>
      )}
    </div>
  );
}

export default function FormularioAmbiental({ cultivoId, onGuardado, onCancelar }) {
  const [form, setForm] = useState({
    temperatura:      "",
    humedad_relativa: "",
    precipitacion_mm: "",
    radiacion_solar:  "",
    velocidad_viento: "",
    origen_dato:      "manual",
    observaciones:    "",
  });
  const [erroresCampo, setErroresCampo] = useState({});
  const [guardadoOffline, setGuardadoOffline] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [error,     setError]     = useState("");
  // DATA-003 FIX: bandera para deshabilitar botón tras primer envío
  const enviandoRef = useRef(false);

  const cambio = (e) => {
    setForm(p => ({ ...p, [e.target.name]: e.target.value }));
    setError("");
    if (erroresCampo[e.target.name]) {
      setErroresCampo(p => ({ ...p, [e.target.name]: "" }));
    }
  };

  // DATA-001 FIX: validar que al menos un campo numérico tenga valor
  // y que los valores estén dentro de rangos físicos plausibles
  const validar = () => {
    const numericos = ["temperatura", "humedad_relativa", "precipitacion_mm", "radiacion_solar", "velocidad_viento"];
    const nuevosErrores = {};

    // Al menos un campo numérico con valor (DATA-001)
    const algunoConValor = numericos.some(k => form[k] !== "");
    if (!algunoConValor) {
      setError("Debes ingresar al menos una variable ambiental antes de guardar.");
      return false;
    }

    // Validar rangos de los campos que tienen valor (DATA-002)
    numericos.forEach(key => {
      if (form[key] === "") return;
      const val = parseFloat(form[key]);
      const rango = RANGOS[key];
      if (isNaN(val)) {
        nuevosErrores[key] = "Debe ser un número válido";
      } else if (val < rango.min || val > rango.max) {
        nuevosErrores[key] = `Rango permitido: ${rango.min} a ${rango.max}`;
      }
    });

    setErroresCampo(nuevosErrores);
    return Object.keys(nuevosErrores).length === 0;
  };

  const enviar = async (e) => {
    e.preventDefault();
    if (!validar()) return;

    // DATA-003 FIX: evitar doble envío
    if (enviandoRef.current) return;
    enviandoRef.current = true;
    setGuardando(true);
    setError("");

    const payload = { origen_dato: form.origen_dato };
    if (form.observaciones) payload.observaciones = form.observaciones;
    const numericos = ["temperatura", "humedad_relativa", "precipitacion_mm", "radiacion_solar", "velocidad_viento"];
    numericos.forEach(k => {
      if (form[k] !== "") payload[k] = parseFloat(form[k]);
    });

    try {
      const resultado = await ambientalService.registrar(cultivoId, payload);
      onGuardado(resultado);
    } catch (e) {
      // OFF-002 FIX: si es error de red, guardar en cola offline
      const esErrorRed = e.message.includes("conexión") || e.message.includes("fetch") ||
                         e.name === "TypeError" || e.message.includes("Failed to fetch") ||
                         e.message.includes("NetworkError");
      if (esErrorRed) {
        encolarAmbiental(cultivoId, payload);
        setGuardadoOffline(true);
        setError("");
        // Notificar al componente padre con un resultado vacío indicando guardado offline
        onGuardado({ offline: true });
      } else {
        setError(e.message);
        // DATA-003 FIX: permitir reintentar tras error del servidor
        enviandoRef.current = false;
      }
    } finally {
      setGuardando(false);
    }
  };

  return (
    <form onSubmit={enviar} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>

      <div style={{
        background: COLOR.fondo,
        borderRadius: "8px",
        padding: "0.75rem 1rem",
        fontSize: "0.82rem",
        color: "#7a5c3a",
        border: `1px solid ${COLOR.borde}`,
      }}>
        {/* DATA-001: información clara sobre el requisito mínimo */}
        Ingresa al menos <strong>una variable ambiental</strong>. Los campos vacíos serán ignorados.
        RF-03 · RNF-10.
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.85rem" }}>
        <Campo
          label="Temperatura (°C)"
          name="temperatura"
          value={form.temperatura}
          onChange={cambio}
          placeholder="Ej: 22.5"
          ayuda="Rango: -10 a 55"
          errorMsg={erroresCampo.temperatura}
        />
        <Campo
          label="Humedad relativa (%)"
          name="humedad_relativa"
          value={form.humedad_relativa}
          onChange={cambio}
          placeholder="Ej: 78.3"
          ayuda="Rango: 0 a 100"
          errorMsg={erroresCampo.humedad_relativa}
        />
        <Campo
          label="Precipitación (mm)"
          name="precipitacion_mm"
          value={form.precipitacion_mm}
          onChange={cambio}
          placeholder="Ej: 12.0"
          errorMsg={erroresCampo.precipitacion_mm}
        />
        <Campo
          label="Radiación solar (W/m²)"
          name="radiacion_solar"
          value={form.radiacion_solar}
          onChange={cambio}
          placeholder="Ej: 420.0"
          errorMsg={erroresCampo.radiacion_solar}
        />
        <Campo
          label="Viento (km/h)"
          name="velocidad_viento"
          value={form.velocidad_viento}
          onChange={cambio}
          placeholder="Ej: 8.5"
          errorMsg={erroresCampo.velocidad_viento}
        />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
        <label style={{ fontSize: "0.82rem", fontWeight: 600, color: "#4a2c0a" }}>
          Origen del dato
        </label>
        <select
          name="origen_dato"
          value={form.origen_dato}
          onChange={cambio}
          style={{
            padding: "0.55rem 0.85rem",
            border: `1.5px solid ${COLOR.borde}`,
            borderRadius: "8px",
            fontSize: "0.9rem",
          }}
        >
          <option value="manual">Manual (ingreso del caficultor)</option>
          <option value="sensor_iot">Sensor IoT</option>
          <option value="api_externa">API meteorológica externa</option>
        </select>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
        <label style={{ fontSize: "0.82rem", fontWeight: 600, color: "#4a2c0a" }}>
          Observaciones
        </label>
        <textarea
          name="observaciones"
          value={form.observaciones}
          onChange={cambio}
          rows={2}
          placeholder="Notas adicionales sobre la lectura..."
          style={{
            padding: "0.55rem 0.85rem",
            border: `1.5px solid ${COLOR.borde}`,
            borderRadius: "8px",
            fontSize: "0.9rem",
            resize: "vertical",
          }}
        />
      </div>

      {/* OFF-002 FIX: notificación de guardado offline */}
      {guardadoOffline && (
        <div style={{
          background: "#fffbeb", border: "1px solid #c8a000",
          borderRadius: "8px", padding: "0.7rem", color: "#92400e", fontSize: "0.85rem",
        }} role="status">
          📶 Sin conexión — la lectura fue guardada localmente y se sincronizará automáticamente cuando se restaure la red.
        </div>
      )}

      {error && (
        <div style={{
          background: "#fff1f0", border: "1px solid #ffccc7",
          borderRadius: "8px", padding: "0.7rem", color: COLOR.rojo, fontSize: "0.85rem",
        }} role="alert">
          {error}
        </div>
      )}

      <div style={{ display: "flex", gap: "0.8rem", justifyContent: "flex-end" }}>
        <button type="button" onClick={onCancelar}
          disabled={guardando}
          style={{
            padding: "0.6rem 1.2rem", borderRadius: "8px",
            border: `1px solid ${COLOR.borde}`, background: "#f5f0eb",
            color: COLOR.cafe, fontWeight: 700, cursor: "pointer",
          }}>
          Cancelar
        </button>
        {/* DATA-003 FIX: deshabilitado durante el guardado */}
        <button type="submit" disabled={guardando}
          aria-disabled={guardando}
          style={{
            padding: "0.6rem 1.4rem", borderRadius: "8px",
            border: "none",
            background: guardando ? "#c9a88a" : COLOR.cafe,
            color: "#fff", fontWeight: 700,
            cursor: guardando ? "not-allowed" : "pointer",
          }}>
          {guardando ? "Guardando..." : "Guardar lectura"}
        </button>
      </div>
    </form>
  );
}
