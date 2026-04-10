// ==============================================================
// modulo_06_mercado / frontend/src/pages/Mercado.jsx
// Dashboard Mercado — RF-13 análisis precios · RF-14 demanda
// RNF-02: interfaz legible para Comercializador sin perfil técnico
// ==============================================================

import { useState, useEffect } from "react";
import { mercadoService } from "../services/mercadoService";

const C = {
  cafe: "#6f3a1b", cafeCla: "#a0522d", verde: "#2d7a3a",
  amarillo: "#c8a000", rojo: "#b91c1c", azul: "#0284c7",
  gris: "#f9f3ee", borde: "#d4b896", texto: "#1a0e05",
};

const TENDENCIA = {
  alza:    { color: C.verde,    icono: "↑", label: "Al alza" },
  baja:    { color: C.rojo,     icono: "↓", label: "A la baja" },
  estable: { color: C.azul,     icono: "→", label: "Estable" },
  volatil: { color: C.amarillo, icono: "~", label: "Volátil" },
};

const DEMANDA = {
  muy_alta: { color: "#7c3aed", label: "Muy Alta ↑↑" },
  alta:     { color: C.verde,   label: "Alta ↑" },
  media:    { color: C.azul,    label: "Media →" },
  baja:     { color: C.rojo,    label: "Baja ↓" },
};

// ── KPI Card ─────────────────────────────────────────────────
function KpiCard({ titulo, valor, subtitulo, color, icono, alerta }) {
  return (
    <div style={{
      background: alerta ? "#fff7ed" : "#fff",
      border: `2px solid ${alerta ? C.amarillo : C.borde}`,
      borderRadius: "14px", padding: "1.2rem 1.4rem",
      display: "flex", flexDirection: "column", gap: "0.3rem",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <p style={{ margin: 0, fontSize: "0.82rem", fontWeight: 600, color: "#9a7a5a" }}>
          {titulo}
        </p>
        {alerta && <span style={{ fontSize: "1rem" }}>⚠️</span>}
        {icono && !alerta && <span style={{ fontSize: "1.2rem" }}>{icono}</span>}
      </div>
      <p style={{ margin: 0, fontSize: "1.6rem", fontWeight: 900, color: color || C.cafe }}>
        {valor ?? "—"}
      </p>
      {subtitulo && (
        <p style={{ margin: 0, fontSize: "0.78rem", color: "#7a5c3a" }}>{subtitulo}</p>
      )}
    </div>
  );
}

// ── Gráfica de barras simple ──────────────────────────────────
function GraficaBarras({ datos, label }) {
  if (!datos || datos.length === 0)
    return <p style={{ color: "#9a7a5a", fontSize: "0.85rem" }}>Sin datos suficientes para graficar.</p>;

  const maximo = Math.max(...datos.map(d => d.precio_prom));
  return (
    <div>
      <p style={{ margin: "0 0 0.8rem", fontWeight: 700, color: C.cafe, fontSize: "0.9rem" }}>
        {label}
      </p>
      <div style={{ display: "flex", alignItems: "flex-end", gap: "6px", height: "120px" }}>
        {datos.map((d, i) => {
          const h = maximo > 0 ? Math.max(8, (d.precio_prom / maximo) * 110) : 8;
          return (
            <div key={d.mes} style={{ flex: 1, display: "flex", flexDirection: "column",
              alignItems: "center", gap: "4px" }}>
              <span style={{ fontSize: "0.65rem", color: "#9a7a5a" }}>
                ${(d.precio_prom / 1000).toFixed(1)}k
              </span>
              <div title={`${d.mes}: $${d.precio_prom.toLocaleString("es-CO")}/kg`}
                style={{
                  width: "100%", height: `${h}px`,
                  background: i === datos.length - 1 ? C.cafe : C.cafeCla,
                  borderRadius: "4px 4px 0 0", cursor: "help",
                }} />
              <span style={{ fontSize: "0.6rem", color: "#9a7a5a",
                transform: "rotate(-40deg)", display: "block", whiteSpace: "nowrap" }}>
                {d.mes.slice(5)}
              </span>
            </div>
          );
        })}
      </div>
      <div style={{ display: "flex", gap: "1rem", marginTop: "0.8rem", flexWrap: "wrap" }}>
        <span style={{ fontSize: "0.75rem", color: C.cafe }}>■ Mes actual</span>
        <span style={{ fontSize: "0.75rem", color: C.cafeCla }}>■ Meses anteriores</span>
      </div>
    </div>
  );
}

// ── Panel análisis precios ─────────────────────────────────────
function PanelAnalisisPrecios({ onAnalizado }) {
  const [params, setParams]     = useState({ meses: 6, tipo: "pergamino_seco", fuente: "todas" });
  const [resultado, setResult]  = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError]       = useState("");

  const ejecutar = async () => {
    setCargando(true); setError("");
    try {
      const r = await mercadoService.analizarPrecios(params);
      setResult(r);
      onAnalizado && onAnalizado();
    } catch (e) { setError(e.message); }
    finally { setCargando(false); }
  };

  const tcfg = resultado ? TENDENCIA[resultado.tendencia] : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.6rem" }}>
        {[
          ["Meses a analizar", "meses", "number", null],
          ["Tipo de café", "tipo", "select", [
            { v: "pergamino_seco", l: "Pergamino seco" },
            { v: "verde_exportacion", l: "Verde exportación" },
            { v: "especial", l: "Especial" },
          ]],
          ["Fuente de datos", "fuente", "select", [
            { v: "todas", l: "Todas las fuentes" },
            { v: "fnc", l: "FNC" },
            { v: "propio_sistema", l: "Ventas propias" },
            { v: "mercado_local", l: "Mercado local" },
          ]],
        ].map(([label, key, tipo, opts]) => (
          <div key={key}>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600,
              color: "#7a5c3a", marginBottom: "0.2rem" }}>{label}</label>
            {opts
              ? <select value={params[key]}
                  onChange={e => setParams(p => ({ ...p, [key]: e.target.value }))}
                  style={estiloInput}>
                  {opts.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
                </select>
              : <input type={tipo} value={params[key]} min="1" max="24"
                  onChange={e => setParams(p => ({ ...p, [key]: parseInt(e.target.value) || 6 }))}
                  style={estiloInput} />
            }
          </div>
        ))}
      </div>

      {error && <p style={{ color: C.rojo, fontSize: "0.82rem", margin: 0 }}>{error}</p>}
      <button onClick={ejecutar} disabled={cargando} style={{
        padding: "0.7rem", borderRadius: "8px", border: "none",
        background: cargando ? "#c9a88a" : C.cafe, color: "#fff",
        fontWeight: 700, cursor: cargando ? "not-allowed" : "pointer",
      }}>
        {cargando ? "Analizando..." : "📈 Ejecutar Análisis de Precios"}
      </button>

      {resultado && tcfg && (
        <div style={{
          background: tcfg.color + "12",
          border: `2px solid ${tcfg.color}`,
          borderRadius: "12px", padding: "1.2rem",
        }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.8rem",
            marginBottom: "1rem" }}>
            <div style={{ textAlign: "center" }}>
              <p style={{ margin: 0, fontSize: "0.75rem", color: "#7a5c3a" }}>Promedio</p>
              <p style={{ margin: 0, fontSize: "1.2rem", fontWeight: 800, color: C.cafe }}>
                ${resultado.precio_promedio?.toLocaleString("es-CO")}
              </p>
            </div>
            <div style={{ textAlign: "center" }}>
              <p style={{ margin: 0, fontSize: "0.75rem", color: "#7a5c3a" }}>Tendencia</p>
              <p style={{ margin: 0, fontSize: "1.2rem", fontWeight: 800, color: tcfg.color }}>
                {tcfg.icono} {tcfg.label}
              </p>
            </div>
            <div style={{ textAlign: "center" }}>
              <p style={{ margin: 0, fontSize: "0.75rem", color: "#7a5c3a" }}>Proyectado</p>
              <p style={{ margin: 0, fontSize: "1.2rem", fontWeight: 800, color: C.azul }}>
                {resultado.precio_proyectado
                  ? `$${resultado.precio_proyectado.toLocaleString("es-CO")}`
                  : "—"}
              </p>
            </div>
          </div>

          {resultado.variacion_label && (
            <p style={{ margin: "0 0 0.5rem", fontSize: "0.85rem",
              color: resultado.variacion_pct >= 0 ? C.verde : C.rojo, fontWeight: 600 }}>
              {resultado.variacion_pct >= 0 ? "↑" : "↓"} {resultado.variacion_label}
            </p>
          )}

          {resultado.alerta_activa && (
            <div style={{ background: "#fff7ed", border: `1px solid ${C.amarillo}`,
              borderRadius: "8px", padding: "0.7rem", marginBottom: "0.7rem" }}>
              <p style={{ margin: 0, color: "#92400e", fontSize: "0.83rem" }}>
                ⚠️ {resultado.mensaje_alerta}
              </p>
            </div>
          )}

          <p style={{ margin: "0.3rem 0 0", fontSize: "0.83rem", color: "#5a3a1a",
            lineHeight: 1.6 }}>
            <strong>Interpretación:</strong> {resultado.interpretacion}
          </p>
          <p style={{ margin: "0.5rem 0 0", fontSize: "0.83rem", color: "#1a5c3a",
            lineHeight: 1.6 }}>
            <strong>Recomendación:</strong> {resultado.recomendacion}
          </p>
          <p style={{ margin: "0.5rem 0 0", fontSize: "0.75rem", color: "#9a7a5a" }}>
            Basado en {resultado.num_registros_base} registro(s) ·
            Min: ${resultado.precio_minimo?.toLocaleString("es-CO")} ·
            Max: ${resultado.precio_maximo?.toLocaleString("es-CO")} ·
            Método: WMA-3
          </p>
        </div>
      )}
    </div>
  );
}

// ── Panel análisis demanda ─────────────────────────────────────
function PanelAnalisisDemanda() {
  const [meses, setMeses]       = useState(6);
  const [obs, setObs]           = useState({ observaciones_mercado: "", oportunidades: "", riesgos: "" });
  const [resultado, setResult]  = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError]       = useState("");

  const ejecutar = async () => {
    setCargando(true); setError("");
    try {
      const r = await mercadoService.analizarDemanda(meses, obs);
      setResult(r);
    } catch (e) { setError(e.message); }
    finally { setCargando(false); }
  };

  const dcfg = resultado ? DEMANDA[resultado.nivel_demanda] : null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div>
        <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600,
          color: "#7a5c3a", marginBottom: "0.2rem" }}>Meses a analizar</label>
        <input type="number" min="1" max="24" value={meses}
          onChange={e => setMeses(parseInt(e.target.value) || 6)}
          style={{ ...estiloInput, width: "100px" }} />
      </div>

      <p style={{ margin: 0, fontSize: "0.8rem", color: "#7a5c3a" }}>
        Observaciones externas (opcional — ferias, pedidos anticipados, tendencias):
      </p>
      {[
        ["Observaciones del mercado", "observaciones_mercado"],
        ["Oportunidades detectadas", "oportunidades"],
        ["Riesgos identificados", "riesgos"],
      ].map(([label, key]) => (
        <div key={key}>
          <label style={{ display: "block", fontSize: "0.78rem", fontWeight: 600,
            color: "#9a7a5a", marginBottom: "0.2rem" }}>{label}</label>
          <textarea value={obs[key]}
            onChange={e => setObs(p => ({ ...p, [key]: e.target.value }))}
            rows={2} style={{ ...estiloInput, width: "100%", resize: "vertical",
              boxSizing: "border-box" }} />
        </div>
      ))}

      {error && <p style={{ color: C.rojo, fontSize: "0.82rem", margin: 0 }}>{error}</p>}
      <button onClick={ejecutar} disabled={cargando} style={{
        padding: "0.7rem", borderRadius: "8px", border: "none",
        background: cargando ? "#c9a88a" : C.cafe, color: "#fff",
        fontWeight: 700, cursor: cargando ? "not-allowed" : "pointer",
      }}>
        {cargando ? "Analizando..." : "📊 Ejecutar Análisis de Demanda"}
      </button>

      {resultado && dcfg && (
        <div style={{
          background: dcfg.color + "12",
          border: `2px solid ${dcfg.color}`,
          borderRadius: "12px", padding: "1.2rem",
        }}>
          <p style={{ margin: "0 0 0.5rem", fontSize: "1rem", fontWeight: 800, color: dcfg.color }}>
            {resultado.nivel_demanda_label}
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.6rem",
            marginBottom: "0.8rem" }}>
            <div style={{ background: "#f9f3ee", borderRadius: "8px", padding: "0.5rem",
              textAlign: "center" }}>
              <p style={{ margin: 0, fontSize: "0.7rem", color: "#9a7a5a" }}>Lotes vendidos</p>
              <p style={{ margin: 0, fontWeight: 800, color: C.cafe }}>
                {resultado.total_lotes_vendidos}
              </p>
            </div>
            <div style={{ background: "#f9f3ee", borderRadius: "8px", padding: "0.5rem",
              textAlign: "center" }}>
              <p style={{ margin: 0, fontSize: "0.7rem", color: "#9a7a5a" }}>Kg vendidos</p>
              <p style={{ margin: 0, fontWeight: 800, color: C.cafe }}>
                {resultado.kg_totales_vendidos?.toLocaleString("es-CO")}
              </p>
            </div>
            <div style={{ background: "#f9f3ee", borderRadius: "8px", padding: "0.5rem",
              textAlign: "center" }}>
              <p style={{ margin: 0, fontSize: "0.7rem", color: "#9a7a5a" }}>Días prom. venta</p>
              <p style={{ margin: 0, fontWeight: 800, color: C.cafe }}>
                {resultado.dias_promedio_venta != null
                  ? `${resultado.dias_promedio_venta.toFixed(1)}d`
                  : "—"}
              </p>
            </div>
          </div>

          {resultado.variacion_label && (
            <p style={{ margin: "0 0 0.4rem", fontSize: "0.83rem",
              color: (resultado.variacion_demanda_pct || 0) >= 0 ? C.verde : C.rojo,
              fontWeight: 600 }}>
              {(resultado.variacion_demanda_pct || 0) >= 0 ? "↑" : "↓"} {resultado.variacion_label}
            </p>
          )}

          {resultado.categoria_mas_demandada && (
            <p style={{ margin: "0 0 0.4rem", fontSize: "0.83rem", color: "#7a5c3a" }}>
              Categoría más demandada: <strong>{resultado.categoria_mas_demandada}</strong>
            </p>
          )}

          <p style={{ margin: "0.3rem 0 0", fontSize: "0.83rem", lineHeight: 1.6, color: "#5a3a1a" }}>
            <strong>Interpretación:</strong> {resultado.interpretacion}
          </p>
          <p style={{ margin: "0.5rem 0 0", fontSize: "0.83rem", lineHeight: 1.6, color: "#1a5c3a" }}>
            <strong>Recomendación:</strong> {resultado.recomendacion}
          </p>
        </div>
      )}
    </div>
  );
}

// ── Componente principal ──────────────────────────────────────
export default function Mercado() {
  const [dashboard, setDashboard] = useState(null);
  const [historial, setHistorial] = useState([]);
  const [tabActiva, setTabActiva] = useState("dashboard");
  const [cargando,  setCargando]  = useState(true);
  const [formPrecio, setFormPrecio] = useState({ visible: false,
    fuente: "fnc", precio_cop_kg: "", fecha_precio: "", tipo_cafe: "pergamino_seco",
    region: "", notas: "" });
  const [mensajeSync, setMensajeSync] = useState("");

  const cargarDashboard = async () => {
    setCargando(true);
    try {
      const [dash, hist] = await Promise.all([
        mercadoService.dashboard(),
        mercadoService.historialPrecios(6),
      ]);
      setDashboard(dash);
      setHistorial(hist);
    } catch (e) { console.error(e); }
    finally { setCargando(false); }
  };

  useEffect(() => { cargarDashboard(); }, []);

  const sincronizar = async () => {
    try {
      const r = await mercadoService.sincronizar();
      setMensajeSync(r.mensaje);
      await cargarDashboard();
    } catch (e) { setMensajeSync(e.message); }
  };

  const guardarPrecio = async () => {
    try {
      await mercadoService.registrarPrecio({
        fuente:        formPrecio.fuente,
        tipo_cafe:     formPrecio.tipo_cafe,
        precio_cop_kg: parseFloat(formPrecio.precio_cop_kg),
        region:        formPrecio.region || null,
        notas:         formPrecio.notas || null,
        fecha_precio:  new Date(formPrecio.fecha_precio).toISOString(),
      });
      setFormPrecio(p => ({ ...p, visible: false, precio_cop_kg: "", fecha_precio: "" }));
      await cargarDashboard();
    } catch (e) { alert(e.message); }
  };

  const TABS = [
    { id: "dashboard",  label: "📊 Resumen" },
    { id: "precios",    label: "💰 Análisis Precios" },
    { id: "demanda",    label: "📈 Análisis Demanda" },
    { id: "registrar",  label: "➕ Registrar Precio" },
  ];

  const tdash = dashboard?.tendencia_precio ? TENDENCIA[dashboard.tendencia_precio] : null;
  const ddash = dashboard?.nivel_demanda_actual;

  return (
    <div style={{ minHeight: "100vh", background: C.gris,
      fontFamily: "'Segoe UI', Roboto, sans-serif", color: C.texto }}>

      {/* Header */}
      <div style={{ background: C.cafe, padding: "1.2rem 2rem",
        display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ margin: 0, color: "#fff", fontSize: "1.5rem", fontWeight: 800 }}>
            📦 Mercado del Café
          </h1>
          <p style={{ margin: 0, color: "#d4b896", fontSize: "0.85rem" }}>
            RF-13 Análisis de precios · RF-14 Análisis de demanda
          </p>
        </div>
        {/* BUG-045 FIX: aria-label para accesibilidad */}
        <button
          aria-label="Sincronizar ventas propias desde trazabilidad"
          onClick={sincronizar}
          style={{
            padding: "0.6rem 1.2rem", borderRadius: "10px",
            border: "none", background: "#fff",
            color: C.cafe, fontWeight: 700, cursor: "pointer",
          }}>
          🔄 Sincronizar ventas
        </button>
      </div>

      {mensajeSync && (
        <div style={{ background: "#f0fdf4", borderBottom: `1px solid ${C.verde}`,
          padding: "0.6rem 2rem", fontSize: "0.85rem", color: C.verde }}>
          ✅ {mensajeSync}
        </div>
      )}

      {dashboard?.alertas?.length > 0 && (
        <div style={{ background: "#fff7ed", borderBottom: `2px solid ${C.amarillo}`,
          padding: "0.6rem 2rem" }}>
          {dashboard.alertas.map((a, i) => (
            <p key={i} style={{ margin: "0.15rem 0", color: "#92400e", fontSize: "0.83rem" }}>
              ⚠️ {a}
            </p>
          ))}
        </div>
      )}

      <div style={{ maxWidth: "1100px", margin: "0 auto", padding: "1.5rem" }}>

        {/* Tabs */}
        <div style={{ display: "flex", borderBottom: `2px solid ${C.borde}`, marginBottom: "1.5rem" }}>
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTabActiva(t.id)} style={{
              padding: "0.6rem 1.2rem", border: "none", background: "none",
              fontWeight: tabActiva === t.id ? 800 : 400,
              color:      tabActiva === t.id ? C.cafe : "#9a7a5a",
              borderBottom: tabActiva === t.id ? `3px solid ${C.cafe}` : "3px solid transparent",
              cursor: "pointer", fontSize: "0.88rem", marginBottom: "-2px",
            }}>{t.label}</button>
          ))}
        </div>

        {/* Dashboard */}
        {tabActiva === "dashboard" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            {cargando && <p style={{ color: "#9a7a5a" }}>Cargando datos...</p>}
            {dashboard && (
              <>
                {/* KPIs */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
                  <KpiCard
                    titulo="Precio actual (venta propia)"
                    valor={dashboard.precio_actual_cop
                      ? `$${dashboard.precio_actual_cop.toLocaleString("es-CO")}/kg`
                      : "Sin datos"}
                    subtitulo={
                      dashboard.diferencial_fnc_pct != null
                        ? `${dashboard.diferencial_fnc_pct >= 0 ? "+" : ""}${dashboard.diferencial_fnc_pct}% vs FNC`
                        : ""}
                    color={C.cafe}
                    icono="💰"
                    alerta={dashboard.alerta_precio}
                  />
                  <KpiCard
                    titulo="Tendencia del precio"
                    valor={tdash ? `${tdash.icono} ${tdash.label}` : "—"}
                    subtitulo={
                      dashboard.precio_proyectado_mes
                        ? `Proyectado: $${dashboard.precio_proyectado_mes.toLocaleString("es-CO")}/kg`
                        : "Sin proyección"}
                    color={tdash?.color}
                    icono="📈"
                  />
                  <KpiCard
                    titulo="Nivel de demanda"
                    valor={ddash || "—"}
                    subtitulo={`${dashboard.total_vendido_mes} lote(s) vendido(s) este mes`}
                    color={C.azul}
                    icono="📊"
                  />
                  <KpiCard
                    titulo="Stock disponible"
                    valor={`${dashboard.lotes_disponibles} lote(s)`}
                    subtitulo={`${dashboard.kg_disponibles?.toLocaleString("es-CO")} kg aprobados`}
                    color={dashboard.lotes_disponibles > 0 ? C.verde : C.rojo}
                    icono="📦"
                  />
                  <KpiCard
                    titulo="Kg vendidos este mes"
                    valor={`${dashboard.kg_vendidos_mes?.toLocaleString("es-CO")} kg`}
                    subtitulo={`en ${dashboard.total_vendido_mes} lote(s)`}
                    color={C.cafeCla}
                    icono="✅"
                  />
                  <KpiCard
                    titulo="Precio FNC referencia"
                    valor={`$${dashboard.precio_fnc_referencia?.toLocaleString("es-CO")}/kg`}
                    subtitulo="Base de comparación"
                    color="#9a7a5a"
                    icono="🏛️"
                  />
                </div>

                {/* Recomendación */}
                <div style={{ background: "#fff", border: `1px solid ${C.borde}`,
                  borderRadius: "14px", padding: "1.2rem 1.5rem" }}>
                  <p style={{ margin: "0 0 0.3rem", fontWeight: 700, color: C.cafe }}>
                    💡 Recomendación comercial
                  </p>
                  <p style={{ margin: 0, fontSize: "0.9rem", lineHeight: 1.7, color: "#5a3a1a" }}>
                    {dashboard.recomendacion_comercial}
                  </p>
                </div>

                {/* Historial gráfica */}
                <div style={{ background: "#fff", border: `1px solid ${C.borde}`,
                  borderRadius: "14px", padding: "1.5rem" }}>
                  <GraficaBarras
                    datos={historial}
                    label="Evolución del precio promedio (COP/kg)"
                  />
                </div>
              </>
            )}
          </div>
        )}

        {/* Análisis precios */}
        {tabActiva === "precios" && (
          <div style={{ background: "#fff", border: `1px solid ${C.borde}`,
            borderRadius: "14px", padding: "1.5rem" }}>
            <h3 style={{ margin: "0 0 1rem", color: C.cafe }}>Análisis Estadístico de Precios</h3>
            <PanelAnalisisPrecios onAnalizado={cargarDashboard} />
          </div>
        )}

        {/* Análisis demanda */}
        {tabActiva === "demanda" && (
          <div style={{ background: "#fff", border: `1px solid ${C.borde}`,
            borderRadius: "14px", padding: "1.5rem" }}>
            <h3 style={{ margin: "0 0 1rem", color: C.cafe }}>Análisis de Demanda del Mercado</h3>
            <PanelAnalisisDemanda />
          </div>
        )}

        {/* Registrar precio */}
        {tabActiva === "registrar" && (
          <div style={{ background: "#fff", border: `1px solid ${C.borde}`,
            borderRadius: "14px", padding: "1.5rem" }}>
            <h3 style={{ margin: "0 0 1rem", color: C.cafe }}>Registrar Precio de Referencia</h3>
            <p style={{ margin: "0 0 1rem", fontSize: "0.85rem", color: "#7a5c3a" }}>
              Ingrese precios de referencia externos (FNC, bolsa de NY, mercado local).
              Los precios de sus propias ventas se sincronizan automáticamente desde el módulo de trazabilidad.
            </p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.7rem" }}>
              {[
                ["Fuente *", "fuente", "select", [
                  { v: "fnc", l: "Precio FNC" },
                  { v: "bolsa_ny", l: "Bolsa New York (Contrato C)" },
                  { v: "mercado_local", l: "Mercado local" },
                  { v: "manual", l: "Manual" },
                ]],
                ["Tipo de café", "tipo_cafe", "select", [
                  { v: "pergamino_seco", l: "Pergamino seco" },
                  { v: "verde_exportacion", l: "Verde exportación" },
                  { v: "tostado", l: "Tostado" },
                  { v: "especial", l: "Especial" },
                ]],
              ].map(([label, key, tipo, opts]) => (
                <div key={key}>
                  <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600,
                    color: "#7a5c3a", marginBottom: "0.2rem" }}>{label}</label>
                  <select value={formPrecio[key]}
                    onChange={e => setFormPrecio(p => ({ ...p, [key]: e.target.value }))}
                    style={estiloInput}>
                    {opts.map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
                  </select>
                </div>
              ))}
              {[
                ["Precio (COP/kg) *", "precio_cop_kg", "number"],
                ["Fecha del precio *", "fecha_precio", "date"],
                ["Región/Ciudad", "region", "text"],
                ["Notas", "notas", "text"],
              ].map(([label, key, tipo]) => (
                <div key={key}>
                  <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600,
                    color: "#7a5c3a", marginBottom: "0.2rem" }}>{label}</label>
                  <input type={tipo} value={formPrecio[key]}
                    onChange={e => setFormPrecio(p => ({ ...p, [key]: e.target.value }))}
                    style={estiloInput} />
                </div>
              ))}
            </div>
            <button onClick={guardarPrecio} style={{
              marginTop: "1rem", padding: "0.7rem 2rem",
              borderRadius: "8px", border: "none",
              background: C.cafe, color: "#fff", fontWeight: 700, cursor: "pointer",
            }}>
              💾 Guardar Precio de Referencia
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

const estiloInput = {
  width: "100%", padding: "0.5rem 0.7rem", borderRadius: "7px",
  border: `1.5px solid #d4b896`, outline: "none", fontSize: "0.88rem",
  fontFamily: "inherit", background: "#fffdf9", color: "#1a0e05",
  boxSizing: "border-box",
};
