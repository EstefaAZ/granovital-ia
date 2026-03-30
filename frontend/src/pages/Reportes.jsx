// ==============================================================
// modulo_07_reportes / frontend/src/pages/Reportes.jsx
// Panel Administrador — RF-18 Reportes y Auditoría
// Diagrama de estados: Solicitado → Generando → Disponible → Descargado
// RNF-02: interfaz legible para Administrador sin perfil técnico
// ==============================================================

import { useState, useEffect, useCallback } from "react";
import { reportesService } from "../services/reportesService";

const C = {
  cafe: "#6f3a1b", cafeCla: "#a0522d", verde: "#2d7a3a",
  rojo: "#b91c1c", azul: "#0284c7", gris: "#f9f3ee",
  borde: "#d4b896", texto: "#1a0e05", amarillo: "#c8a000",
};

const TIPOS_REPORTE = [
  { v: "general",      l: "📊 Resumen general del sistema" },
  { v: "cultivos",     l: "🌱 Cultivos y lotes de producción" },
  { v: "trazabilidad", l: "🔗 Trazabilidad del café" },
  { v: "fitosanitario",l: "🔬 Análisis IA fitosanitario" },
  { v: "ambiental",    l: "🌡️ Monitoreo ambiental y suelo" },
  { v: "mercado",      l: "💰 Precios y análisis de mercado" },
  { v: "usuarios",     l: "👥 Usuarios del sistema" },
];

const ESTADO_BADGE = {
  solicitado:  { bg: "#eff6ff", color: C.azul,     texto: "📋 Solicitado" },
  generando:   { bg: "#fefce8", color: C.amarillo,  texto: "⏳ Generando..." },
  disponible:  { bg: "#f0fdf4", color: C.verde,     texto: "✅ Disponible" },
  error:       { bg: "#fef2f2", color: C.rojo,      texto: "❌ Error" },
  descargado:  { bg: "#f9f3ee", color: C.cafe,      texto: "📥 Descargado" },
};

function Badge({ estado }) {
  const cfg = ESTADO_BADGE[estado] || { bg: "#f3f4f6", color: "#6b7280", texto: estado };
  return (
    <span style={{ background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.color}40`,
      borderRadius: "20px", padding: "2px 10px", fontSize: "0.75rem", fontWeight: 700,
      whiteSpace: "nowrap" }}>
      {cfg.texto}
    </span>
  );
}

function KpiCard({ icono, titulo, valor, color }) {
  return (
    <div style={{ background: "#fff", border: `1px solid ${C.borde}`,
      borderRadius: "12px", padding: "1rem 1.2rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <p style={{ margin: 0, fontSize: "0.8rem", fontWeight: 600, color: "#9a7a5a" }}>{titulo}</p>
        <span style={{ fontSize: "1.2rem" }}>{icono}</span>
      </div>
      <p style={{ margin: "0.3rem 0 0", fontSize: "1.6rem", fontWeight: 900,
        color: color || C.cafe }}>{valor ?? "—"}</p>
    </div>
  );
}

// ── Panel generación de reporte ───────────────────────────────
function PanelGenerarReporte({ onGenerado }) {
  const [tipo,    setTipo]    = useState("general");
  const [nombre,  setNombre]  = useState("");
  const [fi,      setFi]      = useState("");
  const [ff,      setFf]      = useState("");
  const [carg,    setCarg]    = useState(false);
  const [error,   setError]   = useState("");
  const [exito,   setExito]   = useState("");

  const generar = async () => {
    setCarg(true); setError(""); setExito("");
    try {
      const payload = {
        tipo_reporte: tipo,
        nombre:       nombre || null,
        fecha_inicio: fi ? new Date(fi).toISOString() : null,
        fecha_fin:    ff ? new Date(ff).toISOString() : null,
      };
      const r = await reportesService.solicitarReporte(payload);
      setExito(`Reporte "${r.nombre}" generado: ${r.estado_label}`);
      onGenerado && onGenerado();
    } catch (e) { setError(e.message); }
    finally { setCarg(false); }
  };

  return (
    <div style={{ background: "#fff", border: `1px solid ${C.borde}`,
      borderRadius: "14px", padding: "1.5rem" }}>
      <h3 style={{ margin: "0 0 1rem", color: C.cafe }}>
        📄 Generar nuevo reporte
      </h3>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.8rem" }}>
        <div style={{ gridColumn: "1 / -1" }}>
          <label style={estiloLabel}>Tipo de reporte *</label>
          <select value={tipo} onChange={e => setTipo(e.target.value)} style={estiloInput}>
            {TIPOS_REPORTE.map(t => (
              <option key={t.v} value={t.v}>{t.l}</option>
            ))}
          </select>
        </div>

        <div style={{ gridColumn: "1 / -1" }}>
          <label style={estiloLabel}>Nombre del reporte (opcional)</label>
          <input type="text" value={nombre}
            onChange={e => setNombre(e.target.value)}
            placeholder="Se genera automáticamente si no se especifica"
            style={estiloInput} />
        </div>

        <div>
          <label style={estiloLabel}>Fecha inicio (opcional)</label>
          <input type="datetime-local" value={fi}
            onChange={e => setFi(e.target.value)} style={estiloInput} />
        </div>
        <div>
          <label style={estiloLabel}>Fecha fin (opcional)</label>
          <input type="datetime-local" value={ff}
            onChange={e => setFf(e.target.value)} style={estiloInput} />
        </div>
      </div>

      {error && (
        <p style={{ margin: "0.8rem 0 0", color: C.rojo, fontSize: "0.83rem" }}>❌ {error}</p>
      )}
      {exito && (
        <p style={{ margin: "0.8rem 0 0", color: C.verde, fontSize: "0.83rem" }}>✅ {exito}</p>
      )}

      <button onClick={generar} disabled={carg} style={{
        marginTop: "1rem", padding: "0.75rem 2rem", borderRadius: "10px",
        border: "none", background: carg ? "#c9a88a" : C.cafe,
        color: "#fff", fontWeight: 700, cursor: carg ? "not-allowed" : "pointer",
        fontSize: "0.92rem",
      }}>
        {carg ? "⏳ Generando reporte..." : "📊 Generar Reporte"}
      </button>
    </div>
  );
}

// ── Tabla de reportes ─────────────────────────────────────────
function TablaReportes({ reportes, onActualizar }) {
  const [descargando, setDesc] = useState(null);

  const descargar = async (r) => {
    setDesc(r.id_reporte);
    try {
      const blob = await reportesService.descargarReporte(r.id_reporte);
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement("a");
      a.href     = url;
      // BUG-045 FIX: advertir si el reporte es JSON (modo degradado sin reportlab)
      const nombreArchivo = r.nombre_archivo || `reporte_${r.id_reporte}.pdf`;
      if (nombreArchivo.endsWith(".json")) {
        alert("⚠️ Advertencia: reportlab no está instalado en el servidor.\n" +
              "El reporte se descargará como JSON en lugar de PDF.\n" +
              "Instala reportlab en el módulo de reportes: pip install reportlab");
      }
      a.download = nombreArchivo;
      a.click();
      URL.revokeObjectURL(url);
      onActualizar && onActualizar();
    } catch (e) { alert(e.message); }
    finally { setDesc(null); }
  };

  const reintentar = async (id) => {
    try {
      await reportesService.reintentarReporte(id);
      onActualizar && onActualizar();
    } catch (e) { alert(e.message); }
  };

  if (!reportes.length)
    return <p style={{ color: "#9a7a5a", textAlign: "center", padding: "2rem" }}>
      No hay reportes generados aún.
    </p>;

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
        <thead>
          <tr style={{ background: C.cafe }}>
            {["ID","Nombre","Tipo","Estado","Registros","Tamaño","Generado","Acciones"].map(h => (
              <th key={h} style={{ padding: "0.6rem 0.8rem", color: "#fff",
                textAlign: "left", fontWeight: 700, whiteSpace: "nowrap" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {reportes.map((r, i) => (
            <tr key={r.id_reporte} style={{
              background: i % 2 === 0 ? "#fff" : C.gris,
              borderBottom: `1px solid ${C.borde}`,
            }}>
              <td style={estiloTd}>{r.id_reporte}</td>
              <td style={{ ...estiloTd, maxWidth: "200px", overflow: "hidden",
                textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={r.nombre}>
                {r.nombre}
              </td>
              <td style={estiloTd}>
                <span style={{ fontSize: "0.78rem", color: "#7a5c3a" }}>
                  {TIPOS_REPORTE.find(t => t.v === r.tipo_reporte)?.l || r.tipo_reporte}
                </span>
              </td>
              <td style={estiloTd}><Badge estado={r.estado} /></td>
              <td style={{ ...estiloTd, textAlign: "right" }}>
                {r.num_registros ?? "—"}
              </td>
              <td style={{ ...estiloTd, textAlign: "right" }}>
                {r.tamano_kb ? `${r.tamano_kb} KB` : "—"}
              </td>
              <td style={{ ...estiloTd, whiteSpace: "nowrap", fontSize: "0.78rem" }}>
                {r.fecha_generado
                  ? new Date(r.fecha_generado).toLocaleString("es-CO")
                  : "—"}
              </td>
              <td style={{ ...estiloTd, whiteSpace: "nowrap" }}>
                {(r.estado === "disponible" || r.estado === "descargado") && (
                  <button
                    onClick={() => descargar(r)}
                    disabled={descargando === r.id_reporte}
                    style={{
                      padding: "0.3rem 0.7rem", borderRadius: "6px",
                      border: "none", background: C.verde, color: "#fff",
                      fontSize: "0.75rem", fontWeight: 700,
                      cursor: "pointer", marginRight: "4px",
                    }}>
                    {descargando === r.id_reporte ? "..." : "📥"}
                  </button>
                )}
                {r.estado === "error" && (
                  <button
                    aria-label="Reintentar generacion de reporte"
                    onClick={() => reintentar(r.id_reporte)}
                    style={{
                      padding: "0.3rem 0.7rem", borderRadius: "6px",
                      border: "none", background: C.amarillo, color: "#fff",
                      fontSize: "0.75rem", fontWeight: 700, cursor: "pointer",
                    }}>
                    🔄
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ── Panel auditoría ───────────────────────────────────────────
function PanelAuditoria() {
  const [datos,   setDatos]   = useState({ total: 0, registros: [] });
  const [filtros, setFiltros] = useState({
    modulo: "", accion: "", resultado: "", page: 1, page_size: 50,
  });
  const [carg, setCarg] = useState(false);

  const MODULOS = ["","autenticacion","cultivos","monitoreo","ia","trazabilidad","mercado","reportes","sistema"];
  const ACCIONES= ["","crear","leer","actualizar","eliminar","login","logout","exportar","generar_reporte","cambio_estado","error_sistema"];
  const RESULTADOS=["","exitoso","fallido","parcial"];

  const cargar = useCallback(async () => {
    setCarg(true);
    try {
      const params = Object.fromEntries(
        Object.entries(filtros).filter(([,v]) => v !== "" && v !== null)
      );
      const r = await reportesService.consultarAuditoria(params);
      setDatos(r);
    } catch (e) { console.error(e); }
    finally { setCarg(false); }
  }, [filtros]);

  useEffect(() => { cargar(); }, [cargar]);

  const COLOR_RES = {
    exitoso: C.verde, fallido: C.rojo, parcial: C.amarillo,
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      {/* Filtros */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.6rem",
        background: "#fff", border: `1px solid ${C.borde}`, borderRadius: "12px", padding: "1rem" }}>
        {[
          ["Módulo", "modulo", MODULOS],
          ["Acción", "accion", ACCIONES],
          ["Resultado", "resultado", RESULTADOS],
        ].map(([label, key, opts]) => (
          <div key={key}>
            <label style={estiloLabel}>{label}</label>
            <select value={filtros[key]}
              onChange={e => setFiltros(p => ({ ...p, [key]: e.target.value, page: 1 }))}
              style={estiloInput}>
              {opts.map(o => <option key={o} value={o}>{o || "— Todos —"}</option>)}
            </select>
          </div>
        ))}
      </div>

      {/* Tabla */}
      <div style={{ background: "#fff", border: `1px solid ${C.borde}`,
        borderRadius: "12px", overflow: "hidden" }}>
        <div style={{ padding: "0.8rem 1rem", background: C.gris,
          borderBottom: `1px solid ${C.borde}`, display: "flex",
          justifyContent: "space-between", alignItems: "center" }}>
          <p style={{ margin: 0, fontWeight: 700, color: C.cafe, fontSize: "0.88rem" }}>
            Log de Auditoría — {datos.total} evento(s)
          </p>
          <button onClick={cargar} style={{
            padding: "0.3rem 0.8rem", borderRadius: "6px", border: "none",
            background: C.cafe, color: "#fff", fontSize: "0.78rem",
            fontWeight: 700, cursor: "pointer",
          }aria-label="Actualizar lista de reportes">🔄 Actualizar</button>
        </div>

        {carg && <p style={{ padding: "1rem", color: "#9a7a5a" }}>Cargando...</p>}

        {!carg && datos.registros.length === 0 && (
          <p style={{ padding: "2rem", textAlign: "center", color: "#9a7a5a" }}>
            Sin eventos de auditoría con los filtros aplicados.
          </p>
        )}

        {!carg && datos.registros.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
              <thead>
                <tr style={{ background: "#f9f3ee" }}>
                  {["ID","Fecha","Módulo","Acción","Descripción","Resultado","Usuario","IP"].map(h => (
                    <th key={h} style={{ padding: "0.5rem 0.7rem", color: "#7a5c3a",
                      textAlign: "left", fontWeight: 700, whiteSpace: "nowrap",
                      borderBottom: `1px solid ${C.borde}` }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {datos.registros.map((ev, i) => (
                  <tr key={ev.id_auditoria} style={{
                    background: i % 2 === 0 ? "#fff" : C.gris,
                    borderBottom: `1px solid ${C.borde}`,
                  }}>
                    <td style={estiloTd}>{ev.id_auditoria}</td>
                    <td style={{ ...estiloTd, whiteSpace: "nowrap", fontSize: "0.74rem" }}>
                      {new Date(ev.fecha_evento).toLocaleString("es-CO")}
                    </td>
                    <td style={estiloTd}>
                      <code style={{ fontSize: "0.72rem", background: "#f3f4f6",
                        padding: "1px 4px", borderRadius: "3px" }}>{ev.modulo}</code>
                    </td>
                    <td style={estiloTd}>
                      <code style={{ fontSize: "0.72rem", background: "#f3f4f6",
                        padding: "1px 4px", borderRadius: "3px" }}>{ev.accion}</code>
                    </td>
                    <td style={{ ...estiloTd, maxWidth: "250px", overflow: "hidden",
                      textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                      title={ev.descripcion}>
                      {ev.descripcion}
                    </td>
                    <td style={estiloTd}>
                      <span style={{ color: COLOR_RES[ev.resultado] || "#6b7280",
                        fontWeight: 700, fontSize: "0.75rem" }}>
                        {ev.resultado}
                      </span>
                    </td>
                    <td style={{ ...estiloTd, fontSize: "0.74rem" }}>
                      {ev.nombre_usuario || "—"}
                    </td>
                    <td style={{ ...estiloTd, fontSize: "0.72rem", color: "#9a7a5a" }}>
                      {ev.ip_origen || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Paginación */}
        {datos.total_pages > 1 && (
          <div style={{ padding: "0.6rem 1rem", display: "flex",
            justifyContent: "center", gap: "0.5rem",
            borderTop: `1px solid ${C.borde}` }}>
            {Array.from({ length: datos.total_pages }, (_, i) => i + 1).map(p => (
              <button key={p} onClick={() => setFiltros(f => ({ ...f, page: p }))}
                style={{
                  padding: "0.3rem 0.7rem", borderRadius: "6px",
                  border: `1px solid ${C.borde}`,
                  background: filtros.page === p ? C.cafe : "#fff",
                  color:      filtros.page === p ? "#fff" : C.cafe,
                  fontWeight: 700, cursor: "pointer", fontSize: "0.8rem",
                }}>{p}</button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Componente principal ──────────────────────────────────────
export default function Reportes() {
  const [resumen,  setResumen]  = useState(null);
  const [reportes, setReportes] = useState([]);
  const [tab,      setTab]      = useState("panel");
  const [cargando, setCargando] = useState(true);

  const cargarDatos = useCallback(async () => {
    setCargando(true);
    try {
      const [res, reps] = await Promise.all([
        reportesService.resumenSistema(),
        reportesService.listarReportes(),
      ]);
      setResumen(res);
      setReportes(reps);
    } catch (e) { console.error(e); }
    finally { setCargando(false); }
  }, []);

  useEffect(() => { cargarDatos(); }, [cargarDatos]);

  const TABS = [
    { id: "panel",    label: "📊 Panel del sistema" },
    { id: "generar",  label: "📄 Generar reporte" },
    { id: "historial",label: "🗂️ Historial de reportes" },
    { id: "auditoria",label: "🔍 Auditoría" },
  ];

  return (
    <div style={{ minHeight: "100vh", background: C.gris,
      fontFamily: "'Segoe UI', Roboto, sans-serif", color: C.texto }}>

      {/* Header */}
      <div style={{ background: C.cafe, padding: "1.2rem 2rem" }}>
        <h1 style={{ margin: 0, color: "#fff", fontSize: "1.5rem", fontWeight: 800 }}>
          📋 Reportes y Auditoría
        </h1>
        <p style={{ margin: 0, color: "#d4b896", fontSize: "0.85rem" }}>
          RF-18 · Solo Administrador · Diagrama estados: Solicitado → Generando → Disponible → Descargado
        </p>
      </div>

      <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "1.5rem" }}>

        {/* Tabs */}
        <div style={{ display: "flex", borderBottom: `2px solid ${C.borde}`, marginBottom: "1.5rem" }}>
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} style={{
              padding: "0.6rem 1.2rem", border: "none", background: "none",
              fontWeight: tab === t.id ? 800 : 400,
              color:      tab === t.id ? C.cafe : "#9a7a5a",
              borderBottom: tab === t.id ? `3px solid ${C.cafe}` : "3px solid transparent",
              cursor: "pointer", fontSize: "0.88rem", marginBottom: "-2px",
            }}>{t.label}</button>
          ))}
        </div>

        {/* Panel del sistema */}
        {tab === "panel" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.2rem" }}>
            {cargando && <p style={{ color: "#9a7a5a" }}>Cargando...</p>}
            {resumen && (
              <>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "0.8rem" }}>
                  <KpiCard icono="👥" titulo="Usuarios totales"    valor={resumen.total_usuarios}    color={C.azul} />
                  <KpiCard icono="✅" titulo="Usuarios activos"    valor={resumen.usuarios_activos}  color={C.verde} />
                  <KpiCard icono="🌱" titulo="Cultivos registrados" valor={resumen.total_cultivos}   color={C.cafeCla} />
                  <KpiCard icono="📦" titulo="Lotes totales"        valor={resumen.total_lotes}      color={C.cafe} />
                  <KpiCard icono="🔬" titulo="Análisis IA"          valor={resumen.total_analisis_ia} color="#7c3aed" />
                  <KpiCard icono="📈" titulo="Análisis IA (7 días)" valor={resumen.analisis_ultima_semana} color="#7c3aed" />
                  <KpiCard icono="⚙️" titulo="Lotes en proceso"    valor={resumen.lotes_en_proceso} color={C.amarillo} />
                  <KpiCard icono="💼" titulo="Lotes vendidos"       valor={resumen.lotes_vendidos}   color={C.verde} />
                  <KpiCard icono="📊" titulo="Reportes generados"   valor={resumen.reportes_generados} color={C.cafe} />
                  <KpiCard icono="🔍" titulo="Eventos auditoría hoy" valor={resumen.eventos_auditoria_hoy} color={C.azul} />
                  <KpiCard icono="❌" titulo="Errores (7 días)"     valor={resumen.errores_sistema_semana} color={C.rojo} />
                  <KpiCard icono="🕐" titulo="Actualizado"
                    valor={new Date(resumen.fecha_actualizacion).toLocaleTimeString("es-CO")}
                    color="#9a7a5a" />
                </div>
              </>
            )}
          </div>
        )}

        {/* Generar reporte */}
        {tab === "generar" && (
          <PanelGenerarReporte onGenerado={() => { cargarDatos(); setTab("historial"); }} />
        )}

        {/* Historial */}
        {tab === "historial" && (
          <div style={{ background: "#fff", border: `1px solid ${C.borde}`,
            borderRadius: "14px", overflow: "hidden" }}>
            <div style={{ padding: "0.8rem 1.2rem", background: C.gris,
              borderBottom: `1px solid ${C.borde}`, display: "flex",
              justifyContent: "space-between", alignItems: "center" }}>
              <p style={{ margin: 0, fontWeight: 700, color: C.cafe }}>
                Historial de Reportes — {reportes.length} reporte(s)
              </p>
              <button onClick={cargarDatos} style={{
                padding: "0.3rem 0.8rem", borderRadius: "6px", border: "none",
                background: C.cafe, color: "#fff", fontSize: "0.78rem",
                fontWeight: 700, cursor: "pointer",
              }aria-label="Actualizar lista de reportes">🔄 Actualizar</button>
            </div>
            <TablaReportes reportes={reportes} onActualizar={cargarDatos} />
          </div>
        )}

        {/* Auditoría */}
        {tab === "auditoria" && <PanelAuditoria />}
      </div>
    </div>
  );
}

const estiloLabel = {
  display: "block", fontSize: "0.8rem", fontWeight: 600,
  color: "#7a5c3a", marginBottom: "0.2rem",
};
const estiloInput = {
  width: "100%", padding: "0.5rem 0.7rem", borderRadius: "7px",
  border: `1.5px solid #d4b896`, outline: "none", fontSize: "0.88rem",
  fontFamily: "inherit", background: "#fffdf9", color: "#1a0e05",
  boxSizing: "border-box",
};
const estiloTd = {
  padding: "0.5rem 0.7rem", color: "#3a2010",
};
