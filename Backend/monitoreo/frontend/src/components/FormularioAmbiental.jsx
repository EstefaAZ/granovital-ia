// ==============================================================
// modulo_03_monitoreo / frontend/src/components/FormularioAmbiental.jsx
// Formulario de ingreso manual de lectura ambiental
// RF-03 | RNF-02 Usabilidad | RNF-10 Uso sin conectividad IoT
// ==============================================================

import { useState } from "react";
import { ambientalService } from "../services/monitoreoService";

const COLOR = {
  cafe:   "#6f3a1b",
  borde:  "#d4b896",
  fondo:  "#f9f3ee",
  verde:  "#2d7a3a",
  rojo:   "#b91c1c",
};

function Campo({ label, name, value, onChange, tipo = "number", placeholder = "", ayuda = "" }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
      <label style={{ fontSize: "0.82rem", fontWeight: 600, color: "#4a2c0a" }}>
        {label}
      </label>
      <input
        name={name}
        type={tipo}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        step="0.01"
        style={{
          padding:      "0.55rem 0.85rem",
          border:       `1.5px solid ${COLOR.borde}`,
          borderRadius: "8px",
          fontSize:     "0.9rem",
          outline:      "none",
        }}
      />
      {ayuda && (
        <span style={{ fontSize: "0.73rem", color: "#9a7a5a" }}>{ayuda}</span>
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
  const [guardando, setGuardando] = useState(false);
  const [error,     setError]     = useState("");

  const cambio = (e) => {
    setForm(p => ({ ...p, [e.target.name]: e.target.value }));
    setError("");
  };

  const enviar = async (e) => {
    e.preventDefault();
    setGuardando(true);
    setError("");

    // Construir payload solo con campos que tienen valor
    const payload = { origen_dato: form.origen_dato };
    if (form.observaciones) payload.observaciones = form.observaciones;
    const numericos = [
      "temperatura", "humedad_relativa", "precipitacion_mm",
      "radiacion_solar", "velocidad_viento",
    ];
    numericos.forEach(k => {
      if (form[k] !== "") payload[k] = parseFloat(form[k]);
    });

    try {
      const resultado = await ambientalService.registrar(cultivoId, payload);
      onGuardado(resultado);
    } catch (e) {
      setError(e.message);
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
        Ingrese las variables que tenga disponibles.
        Al menos una es obligatoria. RF-03 - RNF-10.
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.85rem" }}>
        <Campo label="Temperatura (C)"        name="temperatura"      value={form.temperatura}
          onChange={cambio} placeholder="Ej: 22.5" ayuda="Rango: -10 a 55" />
        <Campo label="Humedad relativa (%)"   name="humedad_relativa" value={form.humedad_relativa}
          onChange={cambio} placeholder="Ej: 78.3" ayuda="Rango: 0 a 100" />
        <Campo label="Precipitacion (mm)"     name="precipitacion_mm" value={form.precipitacion_mm}
          onChange={cambio} placeholder="Ej: 12.0" />
        <Campo label="Radiacion solar (W/m2)" name="radiacion_solar"  value={form.radiacion_solar}
          onChange={cambio} placeholder="Ej: 420.0" />
        <Campo label="Viento (km/h)"          name="velocidad_viento" value={form.velocidad_viento}
          onChange={cambio} placeholder="Ej: 8.5" />
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
          <option value="api_externa">API meteorologica externa</option>
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
          style={{
            padding: "0.6rem 1.2rem", borderRadius: "8px",
            border: `1px solid ${COLOR.borde}`, background: "#f5f0eb",
            color: COLOR.cafe, fontWeight: 700, cursor: "pointer",
          }}>
          Cancelar
        </button>
        <button type="submit" disabled={guardando}
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
