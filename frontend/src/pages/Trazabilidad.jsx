// ==============================================================
// frontend/src/pages/Trazabilidad.jsx
// Dashboard de Trazabilidad — RF-10, RF-11, RF-12, RF-15
//
// Paneles:
//   Lista de lotes con estado (Diagrama de Estados LOTE)
//   Detalle del lote: información, secado y clasificación
//   Registro de secado con alertas (RF-11)
//   Clasificación del grano FNC (RF-12)
//   Vista pública QR simulada (RN-05)
//   Log de eventos inmutables (RN-04)
//
// QA FIXES sobre la versión original del proyecto:
//   DATA-005 FIX: id_cultivo desde sessionStorage, no hardcodeado a 1
//   DATA-006 FIX: campo fecha_cosecha con max = hoy (no permite fechas futuras)
//   DATA-003 FIX: anti-doble-envío con useRef en formularios
//   UX-001 FIX:  Modal compartido con cierre por tecla Escape (WCAG 2.1)
//   UX-002 FIX:  aria-label en botón cerrar modal
//   UX-005 FIX:  Layout responsive para móvil (grid 1 columna en <768px)
// ==============================================================

import { useState, useEffect, useRef } from "react";
import { trazabilidadService } from "../services/trazabilidadService";
import Modal from "../components/Modal";

const C = {
  cafe: "#6f3a1b", cafeCla: "#a0522d", verde: "#2d7a3a",
  amarillo: "#c8a000", rojo: "#b91c1c", azul: "#0284c7",
  gris: "#f9f3ee", borde: "#d4b896", texto: "#1a0e05",
};

const ESTADO_CONFIG = {
  registrado:   { color: "#6366f1", label: "Registrado",   icono: "📋" },
  disponible:   { color: C.azul,    label: "Disponible",   icono: "✅" },
  en_analisis:  { color: C.amarillo,label: "En Análisis",  icono: "🔬" },
  aprobado:     { color: C.verde,   label: "Aprobado",     icono: "🏆" },
  con_problema: { color: C.rojo,    label: "Con Problema", icono: "⚠️" },
  vendido:      { color: "#059669", label: "Vendido",      icono: "💰" },
  eliminado:    { color: "#9ca3af", label: "Eliminado",    icono: "🗑️" },
};

const CATEGORIA_CONFIG = {
  supremo:       { color: "#7c3aed", label: "Supremo ⭐⭐⭐" },
  excelso_extra: { color: C.verde,   label: "Excelso Extra ⭐⭐" },
  excelso:       { color: C.azul,    label: "Excelso ⭐" },
  corriente:     { color: C.amarillo,label: "Corriente" },
  pasilla:       { color: C.rojo,    label: "Pasilla" },
  sin_clasificar:{ color: "#9ca3af", label: "Sin Clasificar" },
};

// DATA-006 FIX: fecha máxima permitida = hoy
function fechaHoy() {
  return new Date().toISOString().split("T")[0];
}

// ── Subcomponentes ────────────────────────────────────────────

function BadgeEstado({ estado }) {
  const cfg = ESTADO_CONFIG[estado] || { color: "#9ca3af", label: estado, icono: "❓" };
  return (
    <span style={{
      background: cfg.color + "22",
      border: `1.5px solid ${cfg.color}`,
      color: cfg.color,
      borderRadius: "999px",
      padding: "0.2rem 0.75rem",
      fontSize: "0.78rem",
      fontWeight: 700,
    }}>
      {cfg.icono} {cfg.label}
    </span>
  );
}

function TarjetaLote({ lote, seleccionado, onClick }) {
  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      aria-pressed={seleccionado}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onClick(); }}
      style={{
        background: seleccionado ? "#fff8f0" : "#fff",
        border: `2px solid ${seleccionado ? C.cafe : C.borde}`,
        borderRadius: "12px", padding: "1rem 1.2rem",
        cursor: "pointer", transition: "all 0.15s",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <p style={{ margin: 0, fontWeight: 800, color: C.cafe, fontSize: "1rem" }}>
            {lote.codigo_lote}
          </p>
          <p style={{ margin: "0.15rem 0 0", fontSize: "0.82rem", color: "#7a5c3a" }}>
            {lote.variedad_cafe?.replace("_", " ").toUpperCase()} —{" "}
            {lote.kg_cereza_cosechados?.toLocaleString()} kg cereza
          </p>
        </div>
        <BadgeEstado estado={lote.estado} />
      </div>
      {lote.clasificacion_calidad && lote.clasificacion_calidad !== "sin_clasificar" && (
        <p style={{ margin: "0.4rem 0 0", fontSize: "0.8rem",
          color: CATEGORIA_CONFIG[lote.clasificacion_calidad]?.color }}>
          {CATEGORIA_CONFIG[lote.clasificacion_calidad]?.label}
        </p>
      )}
    </div>
  );
}

function FormularioLote({ cultivoId, onCrear, onCancelar }) {
  const [form, setForm] = useState({
    variedad_cafe:        "castillo",
    fecha_cosecha:        "",
    metodo_cosecha:       "manual_selectiva",
    kg_cereza_cosechados: "",
    // DATA-005 FIX: id_cultivo desde sessionStorage, no hardcodeado a 1
    id_cultivo:           cultivoId,
    metodo_beneficio:     "",
  });
  const [cargando, setCargando] = useState(false);
  const [error, setError]       = useState("");
  const enviandoRef = useRef(false); // DATA-003

  const guardar = async () => {
    if (!form.fecha_cosecha || !form.kg_cereza_cosechados) {
      setError("Fecha de cosecha y kilogramos son obligatorios."); return;
    }
    // DATA-006 FIX: no permitir fechas futuras
    if (form.fecha_cosecha > fechaHoy()) {
      setError("La fecha de cosecha no puede ser en el futuro."); return;
    }
    if (enviandoRef.current) return; // DATA-003
    enviandoRef.current = true;
    setCargando(true); setError("");
    try {
      const lote = await trazabilidadService.crearLote({
        ...form,
        kg_cereza_cosechados: parseFloat(form.kg_cereza_cosechados),
        fecha_cosecha: new Date(form.fecha_cosecha).toISOString(),
      });
      onCrear(lote);
    } catch (e) {
      setError(e.message);
      enviandoRef.current = false;
    } finally {
      setCargando(false);
    }
  };

  const campo = (label, key, tipo = "text", opciones = null) => (
    <div key={key} style={{ marginBottom: "0.8rem" }}>
      <label style={{ display: "block", fontSize: "0.82rem", fontWeight: 600, color: "#7a5c3a", marginBottom: "0.25rem" }}>
        {label}
      </label>
      {opciones
        ? <select value={form[key]} onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))}
            style={estiloInput}>
            {opciones.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
          </select>
        : <input type={tipo} value={form[key]}
            onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))}
            // DATA-006 FIX: max = hoy solo para campo de fecha
            max={key === "fecha_cosecha" ? fechaHoy() : undefined}
            style={estiloInput} />
      }
    </div>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.2rem" }}>
      {campo("Variedad", "variedad_cafe", "text", [
        { v: "castillo",   l: "Castillo" },
        { v: "colombia",   l: "Colombia" },
        { v: "caturra",    l: "Caturra" },
        { v: "cenicafe_1", l: "Cenicafé 1" },
        { v: "otro",       l: "Otro" },
      ])}
      {campo("Fecha de cosecha *", "fecha_cosecha", "date")}
      {campo("Método de cosecha", "metodo_cosecha", "text", [
        { v: "manual_selectiva", l: "Manual Selectiva" },
        { v: "manual_global",    l: "Manual Global" },
        { v: "mecanica",         l: "Mecánica" },
      ])}
      {campo("Kg de cereza cosechados *", "kg_cereza_cosechados", "number")}
      {campo("Método de beneficio", "metodo_beneficio", "text", [
        { v: "",          l: "No definido aún" },
        { v: "lavado",    l: "Lavado" },
        { v: "natural",   l: "Natural" },
        { v: "honey",     l: "Honey" },
        { v: "anaerobic", l: "Anaeróbico" },
      ])}
      {error && <p style={{ color: C.rojo, fontSize: "0.82rem" }} role="alert">{error}</p>}
      <div style={{ display: "flex", gap: "0.6rem", marginTop: "0.5rem" }}>
        {/* DATA-003 FIX: deshabilitado durante envío */}
        <button onClick={guardar} disabled={cargando} aria-disabled={cargando}
          style={{
            flex: 1, padding: "0.7rem", borderRadius: "8px", border: "none",
            background: cargando ? "#c9a88a" : C.cafe, color: "#fff",
            fontWeight: 700, cursor: cargando ? "not-allowed" : "pointer",
          }}>
          {cargando ? "Guardando..." : "Registrar Lote"}
        </button>
        <button onClick={onCancelar}
          style={{ padding: "0.7rem 1rem", borderRadius: "8px",
            border: `1px solid ${C.borde}`, background: "#fff",
            color: C.cafe, cursor: "pointer" }}>
          Cancelar
        </button>
      </div>
    </div>
  );
}

function PanelSecado({ lote }) {
  const [form, setForm] = useState({
    temperatura_c: "", humedad_grano_pct: "",
    horas_transcurridas: "", metodo_secado: "solar",
  });
  const [resultado, setResultado] = useState(null);
  const [resumen,   setResumen]   = useState(null);
  const [cargando,  setCargando]  = useState(false);
  const [error,     setError]     = useState("");
  const enviandoRef = useRef(false); // DATA-003

  useEffect(() => {
    trazabilidadService.resumenSecado(lote.id_lote).then(setResumen).catch(() => {});
  }, [lote.id_lote]);

  const registrar = async () => {
    if (!form.temperatura_c || !form.horas_transcurridas) {
      setError("Temperatura y horas son obligatorios."); return;
    }
    if (enviandoRef.current) return; // DATA-003
    enviandoRef.current = true;
    setCargando(true); setError("");
    try {
      const r = await trazabilidadService.registrarSecado(lote.id_lote, {
        temperatura_c:       parseFloat(form.temperatura_c),
        humedad_grano_pct:   form.humedad_grano_pct ? parseFloat(form.humedad_grano_pct) : null,
        horas_transcurridas: parseInt(form.horas_transcurridas),
        metodo_secado:       form.metodo_secado,
      });
      setResultado(r);
      const res = await trazabilidadService.resumenSecado(lote.id_lote);
      setResumen(res);
    } catch (e) {
      setError(e.message);
      enviandoRef.current = false;
    } finally {
      setCargando(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      {resumen && (
        <div style={{
          background: resumen.proceso_completo ? "#f0fdf4" : "#fffbeb",
          border: `1.5px solid ${resumen.proceso_completo ? C.verde : C.amarillo}`,
          borderRadius: "10px", padding: "1rem",
        }}>
          <p style={{ margin: 0, fontWeight: 700, color: resumen.proceso_completo ? C.verde : C.amarillo }}>
            {resumen.proceso_completo ? "✅ Secado Completo" : "⏳ En Proceso de Secado"}
          </p>
          <p style={{ margin: "0.3rem 0 0", fontSize: "0.85rem", color: "#7a5c3a" }}>
            {resumen.total_lecturas} lecturas · {resumen.horas_totales}h acumuladas ·
            Humedad actual: {resumen.humedad_actual ?? "—"}% (objetivo: {resumen.humedad_objetivo}%)
          </p>
          {resumen.alertas_activas?.length > 0 && (
            <div style={{ marginTop: "0.5rem" }}>
              {resumen.alertas_activas.map((a, i) => (
                <p key={i} style={{ margin: "0.15rem 0", fontSize: "0.8rem", color: C.rojo }}>⚠ {a}</p>
              ))}
            </div>
          )}
          <p style={{ margin: "0.5rem 0 0", fontSize: "0.82rem", color: "#5a3a1a" }}>
            {resumen.recomendacion}
          </p>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.6rem" }}>
        {[
          ["Temperatura (°C) *",     "temperatura_c",       "number"],
          ["Humedad del grano (%)",   "humedad_grano_pct",   "number"],
          ["Horas transcurridas *",  "horas_transcurridas", "number"],
        ].map(([label, key, tipo]) => (
          <div key={key}>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600,
              color: "#7a5c3a", marginBottom: "0.2rem" }}>{label}</label>
            <input type={tipo} value={form[key]}
              onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))}
              style={{ ...estiloInput, width: "100%", boxSizing: "border-box" }} />
          </div>
        ))}
        <div>
          <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600,
            color: "#7a5c3a", marginBottom: "0.2rem" }}>Método de secado</label>
          <select value={form.metodo_secado}
            onChange={e => setForm(p => ({ ...p, metodo_secado: e.target.value }))}
            style={{ ...estiloInput, width: "100%", boxSizing: "border-box" }}>
            <option value="solar">Solar</option>
            <option value="mecanico">Mecánico</option>
            <option value="mixto">Mixto</option>
          </select>
        </div>
      </div>

      {error && <p style={{ color: C.rojo, fontSize: "0.82rem", margin: 0 }} role="alert">{error}</p>}

      <button onClick={registrar} disabled={cargando} aria-disabled={cargando} style={{
        padding: "0.7rem", borderRadius: "8px", border: "none",
        background: cargando ? "#c9a88a" : C.cafe, color: "#fff",
        fontWeight: 700, cursor: cargando ? "not-allowed" : "pointer",
      }}>
        {cargando ? "Registrando..." : "📊 Registrar Lectura de Secado"}
      </button>

      {resultado && (
        <div style={{
          background: resultado.alerta_temperatura ? "#fff7ed" : "#f0fdf4",
          border: `1px solid ${resultado.alerta_temperatura ? C.amarillo : C.verde}`,
          borderRadius: "8px", padding: "0.8rem", fontSize: "0.85rem",
        }}>
          <p style={{ margin: 0, fontWeight: 700 }}>
            Lectura registrada — T: {resultado.temperatura_c}°C
            {resultado.humedad_grano_pct != null && ` · H: ${resultado.humedad_grano_pct}%`}
            {resultado.progreso_humedad_pct != null && ` · Progreso: ${resultado.progreso_humedad_pct}%`}
          </p>
          {resultado.alerta_temperatura && (
            <p style={{ margin: "0.3rem 0 0", color: "#c2410c" }}>⚠ {resultado.alerta_temperatura}</p>
          )}
          {resultado.proceso_completo && (
            <p style={{ margin: "0.3rem 0 0", color: C.verde, fontWeight: 700 }}>
              ✅ Proceso de secado completado. Proceda con la clasificación del grano.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function PanelClasificacion({ lote, onClasificado }) {
  const [form, setForm] = useState({
    numero_defectos: "", humedad_pct: "",
    puntaje_taza: "", metodo: "ia_automatica",
  });
  const [resultado, setResultado] = useState(null);
  const [cargando,  setCargando]  = useState(false);
  const [error,     setError]     = useState("");
  const enviandoRef = useRef(false); // DATA-003

  const clasificar = async () => {
    if (!form.numero_defectos || !form.humedad_pct) {
      setError("Defectos y humedad son obligatorios."); return;
    }
    if (enviandoRef.current) return; // DATA-003
    enviandoRef.current = true;
    setCargando(true); setError("");
    try {
      const r = await trazabilidadService.clasificarGrano(lote.id_lote, {
        numero_defectos: parseInt(form.numero_defectos),
        humedad_pct:     parseFloat(form.humedad_pct),
        puntaje_taza:    form.puntaje_taza ? parseFloat(form.puntaje_taza) : null,
        metodo:          form.metodo,
      });
      setResultado(r);
      onClasificado && onClasificado(r);
    } catch (e) {
      setError(e.message);
      enviandoRef.current = false;
    } finally {
      setCargando(false);
    }
  };

  const catConfig = resultado ? CATEGORIA_CONFIG[resultado.categoria] : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.8rem" }}>
      <p style={{ margin: 0, fontSize: "0.82rem", color: "#7a5c3a" }}>
        Clasifique el grano según la norma FNC de la Federación Nacional de Cafeteros.
        Los criterios son: número de defectos por muestra de 300g y porcentaje de humedad.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.6rem" }}>
        {[
          ["N° de defectos (por 300g) *", "numero_defectos", "number"],
          ["Humedad del grano (%) *",      "humedad_pct",    "number"],
          ["Puntaje de taza SCA (0-100)",  "puntaje_taza",   "number"],
        ].map(([label, key, tipo]) => (
          <div key={key}>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600,
              color: "#7a5c3a", marginBottom: "0.2rem" }}>{label}</label>
            <input type={tipo} value={form[key]}
              onChange={e => setForm(p => ({ ...p, [key]: e.target.value }))}
              style={{ ...estiloInput, width: "100%", boxSizing: "border-box" }} />
          </div>
        ))}
        <div>
          <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600,
            color: "#7a5c3a", marginBottom: "0.2rem" }}>Método</label>
          <select value={form.metodo}
            onChange={e => setForm(p => ({ ...p, metodo: e.target.value }))}
            style={{ ...estiloInput, width: "100%", boxSizing: "border-box" }}>
            <option value="ia_automatica">IA Automática</option>
            <option value="manual">Manual</option>
            <option value="laboratorio">Laboratorio</option>
          </select>
        </div>
      </div>

      {error && <p style={{ color: C.rojo, fontSize: "0.82rem", margin: 0 }} role="alert">{error}</p>}

      <button onClick={clasificar} disabled={cargando} aria-disabled={cargando} style={{
        padding: "0.7rem", borderRadius: "8px", border: "none",
        background: cargando ? "#c9a88a" : C.cafe, color: "#fff",
        fontWeight: 700, cursor: cargando ? "not-allowed" : "pointer",
      }}>
        {cargando ? "Clasificando..." : "🏷️ Clasificar Grano"}
      </button>

      {resultado && catConfig && (
        <div style={{
          background: catConfig.color + "15",
          border: `2px solid ${catConfig.color}`,
          borderRadius: "12px", padding: "1.2rem",
        }}>
          <p style={{ margin: 0, fontSize: "1.1rem", fontWeight: 800, color: catConfig.color }}>
            {catConfig.label}
          </p>
          <p style={{ margin: "0.3rem 0", fontSize: "0.85rem", color: "#7a5c3a" }}>
            {resultado.descripcion_categoria}
          </p>
          <p style={{ margin: "0.3rem 0", fontSize: "0.85rem" }}>
            Precio sugerido: <strong>${resultado.precio_sugerido_kg?.toLocaleString("es-CO")}/kg</strong>
            {resultado.puntaje_taza >= 80 && " ⭐ Specialty Coffee premium"}
          </p>
          <p style={{ margin: "0.5rem 0 0", fontWeight: 700,
            color: resultado.aprobado_exportacion ? C.verde : C.rojo }}>
            {resultado.aprobado_exportacion ? "✅ Apto para exportación FNC" : "❌ No apto para exportación"}
          </p>
          <hr style={{ border: "none", borderTop: `1px solid ${catConfig.color}40`, margin: "0.8rem 0" }} />
          <p style={{ margin: 0, fontSize: "0.85rem" }}>
            <strong>Estado del lote:</strong> <BadgeEstado estado={resultado.estado_lote_nuevo} />
          </p>
          {resultado.estado_lote_nuevo === "aprobado" && (
            <p style={{ margin: "0.5rem 0 0", fontSize: "0.82rem", color: C.verde }}>
              🔗 QR público activado. El consumidor ya puede escanear el código.
            </p>
          )}
          <p style={{ margin: "0.5rem 0 0", fontSize: "0.82rem", lineHeight: 1.6 }}>
            {resultado.recomendacion}
          </p>
        </div>
      )}
    </div>
  );
}

// ── Componente principal ─────────────────────────────────────

export default function Trazabilidad() {
  // DATA-005 FIX: cultivoId desde sessionStorage (escrito por Cultivos.jsx)
  // El original tenía id_cultivo: 1 hardcodeado en FormularioLote
  const cultivoId = sessionStorage.getItem("gv_cultivo_activo")
    ? parseInt(sessionStorage.getItem("gv_cultivo_activo"), 10)
    : null;

  const [lotes,       setLotes]       = useState([]);
  const [loteActivo,  setLoteActivo]  = useState(null);
  const [tabActiva,   setTabActiva]   = useState("secado");
  const [mostrarModal, setMostrarModal] = useState(false); // UX-001 FIX: modal en lugar de inline
  const [cargando,    setCargando]    = useState(true);
  const [eventos,     setEventos]     = useState([]);

  const cargarLotes = async () => {
    setCargando(true);
    try {
      const lista = await trazabilidadService.listarLotes();
      setLotes(lista || []);
    } catch (e) { console.error(e); }
    finally { setCargando(false); }
  };

  useEffect(() => { cargarLotes(); }, []);

  const seleccionar = async (lote) => {
    setLoteActivo(lote);
    setTabActiva("secado");
    try {
      const ev = await trazabilidadService.logEventos(lote.id_lote);
      setEventos(ev || []);
    } catch { setEventos([]); }
  };

  const confirmar = async () => {
    if (!loteActivo) return;
    try {
      await trazabilidadService.confirmarLote(loteActivo.id_lote);
      await cargarLotes();
      const loteActualizado = await trazabilidadService.obtenerLote(loteActivo.id_lote);
      setLoteActivo(loteActualizado);
    } catch (e) { alert(e.message); }
  };

  const TABS = [
    { id: "secado",        label: "🌡️ Secado" },
    { id: "clasificacion", label: "🏷️ Clasificación" },
    { id: "eventos",       label: "📋 Eventos" },
    { id: "qr",            label: "📱 QR Público" },
  ];

  return (
    <div style={{ minHeight: "100vh", background: C.gris, fontFamily: "'Segoe UI', Roboto, sans-serif",
      color: C.texto, display: "flex", flexDirection: "column" }}>

      {/* UX-005 FIX: CSS para layout responsive en móvil */}
      <style>{`
        @media (max-width: 768px) {
          .traza-grid { grid-template-columns: 1fr !important; }
          .traza-panel-izq {
            border-right: none !important;
            border-bottom: 2px solid ${C.borde};
            max-height: 280px;
            overflow-y: auto;
          }
        }
      `}</style>

      {/* Encabezado */}
      <div style={{ background: C.cafe, padding: "1.2rem 2rem",
        display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ margin: 0, color: "#fff", fontSize: "1.5rem", fontWeight: 800 }}>
            📦 Trazabilidad del Café
          </h1>
          <p style={{ margin: 0, color: "#d4b896", fontSize: "0.85rem" }}>
            RF-10 RF-11 RF-12 · RN-02 RN-04 RN-05
          </p>
        </div>
        <button
          onClick={() => setMostrarModal(true)}
          aria-label="Registrar nuevo lote de trazabilidad"
          style={{
            padding: "0.6rem 1.4rem", borderRadius: "10px",
            border: "none", background: "#fff",
            color: C.cafe, fontWeight: 800, cursor: "pointer", fontSize: "0.9rem",
          }}>
          + Nuevo Lote
        </button>
      </div>

      {/* UX-005 FIX: grid con clase CSS responsive */}
      <div className="traza-grid" style={{
        display: "grid", gridTemplateColumns: "320px 1fr",
        flex: 1, overflow: "hidden",
      }}>

        {/* Panel izquierdo — Lista de lotes */}
        <div className="traza-panel-izq" style={{
          borderRight: `2px solid ${C.borde}`, padding: "1.2rem",
          overflowY: "auto", background: "#fff",
        }}>
          <p style={{ margin: "0 0 0.8rem", fontWeight: 700, color: C.cafe }}>
            Mis Lotes ({lotes.length})
          </p>
          {cargando && <p style={{ color: "#9a7a5a", fontSize: "0.85rem" }}>Cargando...</p>}
          {!cargando && lotes.length === 0 && (
            <p style={{ color: "#9a7a5a", fontSize: "0.85rem" }}>
              Sin lotes registrados. Cree el primero con el botón superior.
            </p>
          )}
          <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
            {lotes.map(l => (
              <TarjetaLote
                key={l.id_lote}
                lote={l}
                seleccionado={loteActivo?.id_lote === l.id_lote}
                onClick={() => seleccionar(l)}
              />
            ))}
          </div>
        </div>

        {/* Panel derecho — Detalle */}
        <div style={{ padding: "1.5rem", overflowY: "auto" }}>

          {!loteActivo && (
            <div style={{ textAlign: "center", padding: "4rem 2rem", color: "#9a7a5a" }}>
              <p style={{ fontSize: "3rem" }}>☕</p>
              <p style={{ fontSize: "1.1rem" }}>Seleccione un lote para ver su detalle</p>
            </div>
          )}

          {loteActivo && (
            <div style={{ display: "flex", flexDirection: "column", gap: "1.2rem" }}>
              {/* Header lote */}
              <div style={{ background: "#fff", border: `1px solid ${C.borde}`,
                borderRadius: "14px", padding: "1.2rem 1.5rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between",
                  alignItems: "flex-start", flexWrap: "wrap", gap: "0.5rem" }}>
                  <div>
                    <h2 style={{ margin: 0, color: C.cafe }}>{loteActivo.codigo_lote}</h2>
                    <p style={{ margin: "0.2rem 0 0", color: "#7a5c3a", fontSize: "0.9rem" }}>
                      {loteActivo.variedad_cafe?.replace("_", " ").toUpperCase()} —{" "}
                      {parseFloat(loteActivo.kg_cereza_cosechados).toLocaleString()} kg cosechados
                    </p>
                  </div>
                  <BadgeEstado estado={loteActivo.estado} />
                </div>
                {loteActivo.estado === "registrado" && (
                  <button onClick={confirmar} style={{
                    marginTop: "0.8rem", padding: "0.5rem 1.2rem",
                    borderRadius: "8px", border: "none",
                    background: C.azul, color: "#fff", fontWeight: 700, cursor: "pointer",
                  }}>
                    ✅ Confirmar Lote
                  </button>
                )}
                {loteActivo.codigo_qr && (
                  <p style={{ margin: "0.5rem 0 0", fontSize: "0.82rem", color: C.verde }}>
                    🔗 QR Activo:{" "}
                    <a href={loteActivo.codigo_qr} target="_blank" rel="noreferrer"
                      style={{ color: C.verde }}>{loteActivo.codigo_qr}</a>
                  </p>
                )}
              </div>

              {/* Tabs */}
              <div style={{ display: "flex", borderBottom: `2px solid ${C.borde}`,
                gap: 0, overflowX: "auto" }}>
                {TABS.map(t => (
                  <button key={t.id} onClick={() => setTabActiva(t.id)}
                    role="tab" aria-selected={tabActiva === t.id}
                    style={{
                      padding: "0.55rem 1.1rem", border: "none", background: "none",
                      fontWeight: tabActiva === t.id ? 800 : 400,
                      color:      tabActiva === t.id ? C.cafe : "#9a7a5a",
                      borderBottom: tabActiva === t.id ? `3px solid ${C.cafe}` : "3px solid transparent",
                      cursor: "pointer", fontSize: "0.85rem",
                      marginBottom: "-2px", whiteSpace: "nowrap",
                    }}>{t.label}</button>
                ))}
              </div>

              {/* Contenido tabs */}
              <div style={{ background: "#fff", border: `1px solid ${C.borde}`,
                borderRadius: "14px", padding: "1.5rem" }}>
                {tabActiva === "secado" && <PanelSecado lote={loteActivo} />}
                {tabActiva === "clasificacion" && (
                  <PanelClasificacion lote={loteActivo}
                    onClasificado={async () => {
                      const l = await trazabilidadService.obtenerLote(loteActivo.id_lote);
                      setLoteActivo(l);
                      await cargarLotes();
                    }} />
                )}
                {tabActiva === "eventos" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                    <p style={{ margin: 0, fontWeight: 700, color: C.cafe }}>
                      Log de Eventos (RN-04 — inmutable)
                    </p>
                    {eventos.length === 0 && (
                      <p style={{ color: "#9a7a5a", fontSize: "0.85rem" }}>Sin eventos registrados.</p>
                    )}
                    {eventos.map(ev => (
                      <div key={ev.id_evento} style={{
                        background: "#f9f3ee", borderRadius: "8px",
                        padding: "0.7rem 1rem", fontSize: "0.83rem",
                        borderLeft: `3px solid ${C.cafe}`,
                      }}>
                        <span style={{ fontWeight: 700, color: C.cafe }}>{ev.tipo_evento}</span>
                        {ev.estado_anterior && (
                          <span style={{ color: "#9a7a5a" }}>
                            {" "}· {ev.estado_anterior} → {ev.estado_nuevo}
                          </span>
                        )}
                        <p style={{ margin: "0.2rem 0 0", color: "#5a3a1a" }}>{ev.descripcion}</p>
                        <p style={{ margin: "0.15rem 0 0", color: "#9a7a5a", fontSize: "0.78rem" }}>
                          {new Date(ev.fecha_evento).toLocaleString("es-CO")}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
                {tabActiva === "qr" && (
                  <div style={{ textAlign: "center", padding: "1rem" }}>
                    {loteActivo.codigo_qr
                      ? <>
                          <p style={{ fontWeight: 700, color: C.cafe, marginBottom: "0.5rem" }}>
                            Vista del consumidor (RN-05)
                          </p>
                          <p style={{ fontSize: "0.83rem", color: "#7a5c3a", marginBottom: "1rem" }}>
                            El consumidor escanea el QR del empaque y ve solo la información pública.
                            Nunca ve precios internos, IDs o datos del sistema.
                          </p>
                          <div style={{
                            display: "inline-block", background: C.gris,
                            border: `2px solid ${C.borde}`, borderRadius: "12px", padding: "1.5rem",
                          }}>
                            <p style={{ fontWeight: 800, color: C.cafe, fontSize: "1.1rem" }}>
                              ☕ {loteActivo.codigo_lote}
                            </p>
                            <p style={{ color: "#7a5c3a", fontSize: "0.85rem", margin: "0.2rem 0" }}>
                              {loteActivo.variedad_cafe?.replace("_", " ").toUpperCase()}
                            </p>
                            <p style={{ color: CATEGORIA_CONFIG[loteActivo.clasificacion_calidad]?.color,
                              fontWeight: 700 }}>
                              {CATEGORIA_CONFIG[loteActivo.clasificacion_calidad]?.label}
                            </p>
                            <a href={loteActivo.codigo_qr} target="_blank" rel="noreferrer"
                              style={{ color: C.cafe, fontSize: "0.8rem" }}>
                              Ver trazabilidad completa →
                            </a>
                          </div>
                        </>
                      : <p style={{ color: "#9a7a5a" }}>
                          El QR se activa cuando el lote es aprobado (estado: 'aprobado').
                        </p>
                    }
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* UX-001/002 FIX: Modal compartido con Escape y aria-label */}
      <Modal
        abierto={mostrarModal}
        titulo="Registrar Nuevo Lote"
        onCerrar={() => setMostrarModal(false)}
      >
        <FormularioLote
          cultivoId={cultivoId}
          onCrear={(l) => {
            setLotes(p => [l, ...p]);
            setMostrarModal(false);
            seleccionar(l);
          }}
          onCancelar={() => setMostrarModal(false)}
        />
      </Modal>
    </div>
  );
}

const estiloInput = {
  width: "100%", padding: "0.5rem 0.7rem", borderRadius: "7px",
  border: `1.5px solid #d4b896`, outline: "none", fontSize: "0.88rem",
  fontFamily: "inherit", background: "#fffdf9", color: "#1a0e05",
  boxSizing: "border-box",
};
