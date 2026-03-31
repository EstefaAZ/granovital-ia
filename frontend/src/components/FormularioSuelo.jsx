// ==============================================================
// frontend/src/components/FormularioSuelo.jsx
//
// DATA-002 FIX: validación de rangos físicos plausibles
// DATA-003 FIX: botón deshabilitado tras primer submit hasta respuesta
// ==============================================================

import { useState, useRef } from "react";
import { sueloService } from "../services/monitoreoService";

const COLOR = { cafe: "#6f3a1b", borde: "#d4b896", fondo: "#f9f3ee", rojo: "#b91c1c" };

// DATA-002 FIX: rangos físicos válidos para cada campo de suelo
const RANGOS = {
  ph:               { min: 0,   max: 14,   label: "pH del suelo"             },
  humedad_suelo:    { min: 0,   max: 100,  label: "Humedad del suelo (%)"    },
  nitrogeno:        { min: 0,   max: 1000, label: "Nitrógeno (mg/kg)"        },
  fosforo:          { min: 0,   max: 1000, label: "Fósforo (mg/kg)"          },
  potasio:          { min: 0,   max: 1000, label: "Potasio (mg/kg)"          },
  materia_organica: { min: 0,   max: 100,  label: "Materia orgánica (%)"     },
  conductividad_ec: { min: 0,   max: 20,   label: "Conductividad EC (dS/m)"  },
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
          padding: "0.55rem 0.85rem",
          border: `1.5px solid ${errorMsg ? COLOR.rojo : COLOR.borde}`,
          borderRadius: "8px",
          fontSize: "0.9rem",
          outline: "none",
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

export default function FormularioSuelo({ cultivoId, onGuardado, onCancelar }) {
  const [form, setForm] = useState({
    ph:               "",
    humedad_suelo:    "",
    nitrogeno:        "",
    fosforo:          "",
    potasio:          "",
    materia_organica: "",
    conductividad_ec: "",
    origen_dato:      "manual",
    observaciones:    "",
  });
  const [erroresCampo, setErroresCampo] = useState({});
  const [guardando, setGuardando] = useState(false);
  const [error,     setError]     = useState("");
  // DATA-003 FIX: bandera anti double-submit
  const enviandoRef = useRef(false);

  const cambio = (e) => {
    setForm(p => ({ ...p, [e.target.name]: e.target.value }));
    setError("");
    if (erroresCampo[e.target.name]) {
      setErroresCampo(p => ({ ...p, [e.target.name]: "" }));
    }
  };

  // DATA-002 FIX: validar rangos físicos antes de enviar
  const validar = () => {
    const numericos = Object.keys(RANGOS);
    const nuevosErrores = {};

    // Al menos un campo con valor
    const algunoConValor = numericos.some(k => form[k] !== "");
    if (!algunoConValor) {
      setError("Debes ingresar al menos un dato del análisis de suelo.");
      return false;
    }

    // Validar rangos
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

    // DATA-003 FIX: prevenir doble envío
    if (enviandoRef.current) return;
    enviandoRef.current = true;
    setGuardando(true);
    setError("");

    const payload = { origen_dato: form.origen_dato };
    if (form.observaciones) payload.observaciones = form.observaciones;
    Object.keys(RANGOS).forEach(k => {
      if (form[k] !== "") payload[k] = parseFloat(form[k]);
    });

    try {
      const resultado = await sueloService.registrar(cultivoId, payload);
      onGuardado(resultado);
    } catch (e) {
      setError(e.message);
      // DATA-003 FIX: permitir reintento tras error
      enviandoRef.current = false;
    } finally {
      setGuardando(false);
    }
  };

  return (
    <form onSubmit={enviar} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>

      <div style={{
        background: COLOR.fondo, borderRadius: "8px", padding: "0.75rem 1rem",
        fontSize: "0.82rem", color: "#7a5c3a", border: `1px solid ${COLOR.borde}`,
      }}>
        Ingrese los datos del análisis de suelo. <strong>Al menos un campo es obligatorio.</strong>
        Puede ingresar datos de laboratorio, sensor IoT o medición directa. RF-04.
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.85rem" }}>
        <Campo
          label="pH del suelo"
          name="ph"
          value={form.ph}
          onChange={cambio}
          placeholder="Ej: 6.2"
          ayuda="Escala 0-14. Óptimo café: 5.5-6.5"
          errorMsg={erroresCampo.ph}
        />
        <Campo
          label="Humedad del suelo (%)"
          name="humedad_suelo"
          value={form.humedad_suelo}
          onChange={cambio}
          placeholder="Ej: 55.0"
          ayuda="Rango: 0 a 100"
          errorMsg={erroresCampo.humedad_suelo}
        />
        <Campo
          label="Nitrógeno (mg/kg)"
          name="nitrogeno"
          value={form.nitrogeno}
          onChange={cambio}
          placeholder="Ej: 28.5"
          ayuda="Mínimo recomendado: 20 mg/kg"
          errorMsg={erroresCampo.nitrogeno}
        />
        <Campo
          label="Fósforo (mg/kg)"
          name="fosforo"
          value={form.fosforo}
          onChange={cambio}
          placeholder="Ej: 18.0"
          ayuda="Mínimo recomendado: 15 mg/kg"
          errorMsg={erroresCampo.fosforo}
        />
        <Campo
          label="Potasio (mg/kg)"
          name="potasio"
          value={form.potasio}
          onChange={cambio}
          placeholder="Ej: 25.0"
          ayuda="Mínimo recomendado: 20 mg/kg"
          errorMsg={erroresCampo.potasio}
        />
        <Campo
          label="Materia orgánica (%)"
          name="materia_organica"
          value={form.materia_organica}
          onChange={cambio}
          placeholder="Ej: 3.8"
          ayuda="Rango: 0 a 100"
          errorMsg={erroresCampo.materia_organica}
        />
        <Campo
          label="Conductividad EC (dS/m)"
          name="conductividad_ec"
          value={form.conductividad_ec}
          onChange={cambio}
          placeholder="Ej: 0.45"
          ayuda="Rango: 0 a 20"
          errorMsg={erroresCampo.conductividad_ec}
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
          <option value="manual">Manual (medición directa)</option>
          <option value="laboratorio">Laboratorio certificado</option>
          <option value="sensor_iot">Sensor IoT de suelo</option>
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
          placeholder="Ej: Muestra compuesta de 5 puntos. CENICAFE Lab 2025."
          style={{
            padding: "0.55rem 0.85rem",
            border: `1.5px solid ${COLOR.borde}`,
            borderRadius: "8px",
            fontSize: "0.9rem",
            resize: "vertical",
          }}
        />
      </div>

      {error && (
        <div style={{
          background: "#fff1f0", border: "1px solid #ffccc7",
          borderRadius: "8px", padding: "0.7rem",
          color: COLOR.rojo, fontSize: "0.85rem",
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
          {guardando ? "Guardando..." : "Guardar análisis"}
        </button>
      </div>
    </form>
  );
}
