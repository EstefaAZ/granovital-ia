// ==============================================================
// modulo_03_monitoreo / frontend/src/components/FormularioSuelo.jsx
// Formulario de ingreso de lectura del estado del suelo
// RF-04 | RNF-02 Usabilidad | RNF-10 Ingreso manual
// ==============================================================

import { useState } from "react";
import { sueloService } from "../services/monitoreoService";

const COLOR = { cafe: "#6f3a1b", borde: "#d4b896", fondo: "#f9f3ee", rojo: "#b91c1c" };

function Campo({ label, name, value, onChange, placeholder = "", ayuda = "" }) {
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
          border: `1.5px solid ${COLOR.borde}`,
          borderRadius: "8px",
          fontSize: "0.9rem",
          outline: "none",
        }}
      />
      {ayuda && (
        <span style={{ fontSize: "0.73rem", color: "#9a7a5a" }}>{ayuda}</span>
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

    const payload = { origen_dato: form.origen_dato };
    if (form.observaciones) payload.observaciones = form.observaciones;
    const numericos = [
      "ph", "humedad_suelo", "nitrogeno", "fosforo",
      "potasio", "materia_organica", "conductividad_ec",
    ];
    numericos.forEach(k => {
      if (form[k] !== "") payload[k] = parseFloat(form[k]);
    });

    try {
      const resultado = await sueloService.registrar(cultivoId, payload);
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
        background: COLOR.fondo, borderRadius: "8px", padding: "0.75rem 1rem",
        fontSize: "0.82rem", color: "#7a5c3a", border: `1px solid ${COLOR.borde}`,
      }}>
        Ingrese los datos del analisis de suelo. Al menos un campo es obligatorio.
        Puede ingresar datos de laboratorio, sensor IoT o medicion directa. RF-04.
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.85rem" }}>
        <Campo label="pH del suelo"           name="ph"               value={form.ph}
          onChange={cambio} placeholder="Ej: 6.2" ayuda="Escala 0-14. Optimo cafe: 5.5-6.5" />
        <Campo label="Humedad del suelo (%)"  name="humedad_suelo"    value={form.humedad_suelo}
          onChange={cambio} placeholder="Ej: 55.0" ayuda="Rango: 0 a 100" />
        <Campo label="Nitrogeno (mg/kg)"      name="nitrogeno"        value={form.nitrogeno}
          onChange={cambio} placeholder="Ej: 28.5" ayuda="Minimo recomendado: 20 mg/kg" />
        <Campo label="Fosforo (mg/kg)"        name="fosforo"          value={form.fosforo}
          onChange={cambio} placeholder="Ej: 18.0" ayuda="Minimo recomendado: 15 mg/kg" />
        <Campo label="Potasio (mg/kg)"        name="potasio"          value={form.potasio}
          onChange={cambio} placeholder="Ej: 25.0" ayuda="Minimo recomendado: 20 mg/kg" />
        <Campo label="Materia organica (%)"   name="materia_organica" value={form.materia_organica}
          onChange={cambio} placeholder="Ej: 3.8" />
        <Campo label="Conductividad EC (dS/m)" name="conductividad_ec" value={form.conductividad_ec}
          onChange={cambio} placeholder="Ej: 0.45" />
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
          <option value="manual">Manual (medicion directa)</option>
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
          {guardando ? "Guardando..." : "Guardar analisis"}
        </button>
      </div>
    </form>
  );
}
