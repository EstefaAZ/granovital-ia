// ==============================================================
// modulo_02_cultivos / frontend/src/pages/Cultivos.jsx
// Vista principal de Gestion de Cultivos y Lotes
// RF-03 Cultivos | RF-04 Lotes | RNF-02 Usabilidad
// RNF-07 Funciona en web y movil (responsive)
// ==============================================================

import { useState, useEffect, useCallback } from "react";
import { cultivoService, loteService } from "../services/cultivoService";

// Paleta de colores GranoVital
const COLOR = {
  cafe:      "#6f3a1b",
  cafeCLaro: "#a0522d",
  verde:     "#2d7a3a",
  amarillo:  "#c8a000",
  rojo:      "#b91c1c",
  gris:      "#f5f0eb",
  texto:     "#1a0e05",
  borde:     "#d4b896",
};

// Etiquetas de estado del Cultivo (diagrama de estados)
const ESTADO_CULTIVO = {
  creado:                  { texto: "Creado",             color: COLOR.amarillo },
  en_seguimiento:          { texto: "En Seguimiento",     color: COLOR.verde    },
  con_problema_detectado:  { texto: "Con Problema",       color: COLOR.rojo     },
  tratamiento_aplicado:    { texto: "En Tratamiento",     color: "#7c3aed"      },
  finalizado:              { texto: "Finalizado",         color: "#64748b"      },
  eliminado:               { texto: "Eliminado",          color: "#94a3b8"      },
};

// Etiquetas de estado del Lote (diagrama de estados)
const ESTADO_LOTE = {
  registrado:  { texto: "Registrado",  color: COLOR.amarillo },
  disponible:  { texto: "Disponible",  color: "#0284c7"      },
  en_analisis: { texto: "En Analisis", color: "#7c3aed"      },
  aprobado:    { texto: "Aprobado",    color: COLOR.verde    },
  con_problema:{ texto: "Con Problema",color: COLOR.rojo     },
  vendido:     { texto: "Vendido",     color: "#64748b"      },
  eliminado:   { texto: "Eliminado",   color: "#94a3b8"      },
};

// ==============================================================
// COMPONENTES REUTILIZABLES
// ==============================================================

function Badge({ estado, mapa }) {
  const cfg = mapa[estado] || { texto: estado, color: "#94a3b8" };
  return (
    <span style={{
      background:   cfg.color + "22",
      color:        cfg.color,
      border:       `1px solid ${cfg.color}55`,
      borderRadius: "20px",
      padding:      "3px 10px",
      fontSize:     "0.78rem",
      fontWeight:   700,
    }}>
      {cfg.texto}
    </span>
  );
}

function Tarjeta({ titulo, valor, icono, color }) {
  return (
    <div style={{
      background:   "#fff",
      border:       `1px solid ${COLOR.borde}`,
      borderRadius: "12px",
      padding:      "1.2rem 1.5rem",
      display:      "flex",
      alignItems:   "center",
      gap:          "1rem",
    }}>
      <span style={{ fontSize: "2rem" }}>{icono}</span>
      <div>
        <p style={{ margin: 0, color: "#7a5c3a", fontSize: "0.8rem", fontWeight: 600 }}>
          {titulo}
        </p>
        <p style={{ margin: 0, fontSize: "1.8rem", fontWeight: 800, color: color || COLOR.cafe }}>
          {valor}
        </p>
      </div>
    </div>
  );
}

function Modal({ abierto, titulo, onCerrar, children }) {
  if (!abierto) return null;
  return (
    <div style={{
      position:   "fixed", inset: 0,
      background: "rgba(0,0,0,0.4)",
      display:    "flex",
      alignItems: "center",
      justifyContent: "center",
      zIndex:     1000,
      padding:    "1rem",
    }}>
      <div style={{
        background:   "#fff",
        borderRadius: "16px",
        padding:      "2rem",
        width:        "100%",
        maxWidth:     "520px",
        maxHeight:    "90vh",
        overflowY:    "auto",
        boxShadow:    "0 20px 60px rgba(0,0,0,0.3)",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1.5rem" }}>
          <h3 style={{ margin: 0, color: COLOR.cafe }}>{titulo}</h3>
          <button
            onClick={onCerrar}
            style={{ background: "none", border: "none", fontSize: "1.5rem", cursor: "pointer" }}
            aria-label="Cerrar modal"
          >
            x
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function Campo({ label, name, value, onChange, type = "text", required = false, placeholder = "" }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
      <label style={{ fontSize: "0.83rem", fontWeight: 600, color: "#4a2c0a" }}>
        {label}{required && " *"}
      </label>
      <input
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        required={required}
        placeholder={placeholder}
        style={{
          padding: "0.6rem 0.9rem",
          border: `1.5px solid ${COLOR.borde}`,
          borderRadius: "8px",
          fontSize: "0.9rem",
          outline: "none",
        }}
      />
    </div>
  );
}

function Boton({ onClick, children, variante = "primario", tipo = "button", desactivado = false }) {
  const estilosBase = {
    padding:      "0.6rem 1.2rem",
    borderRadius: "8px",
    border:       "none",
    fontSize:     "0.9rem",
    fontWeight:   700,
    cursor:       desactivado ? "not-allowed" : "pointer",
    opacity:      desactivado ? 0.6 : 1,
    transition:   "opacity 0.2s",
  };

  const variantes = {
    primario:  { background: COLOR.cafe,      color: "#fff"     },
    secundario:{ background: "#f5f0eb",        color: COLOR.cafe, border: `1px solid ${COLOR.borde}` },
    peligro:   { background: "#fee2e2",        color: COLOR.rojo  },
    verde:     { background: "#dcfce7",        color: COLOR.verde },
  };

  return (
    <button
      type={tipo}
      onClick={onClick}
      disabled={desactivado}
      style={{ ...estilosBase, ...variantes[variante] }}
    >
      {children}
    </button>
  );
}

// ==============================================================
// FORMULARIO CULTIVO
// ==============================================================

function FormularioCultivo({ onGuardar, onCancelar, inicial = {} }) {
  const [form, setForm] = useState({
    nombre_cultivo: inicial.nombre_cultivo || "",
    ubicacion:      inicial.ubicacion      || "",
    area_hectareas: inicial.area_hectareas || "",
    variedad_cafe:  inicial.variedad_cafe  || "",
    observaciones:  inicial.observaciones  || "",
  });

  const cambio = (e) => setForm(p => ({ ...p, [e.target.name]: e.target.value }));

  const enviar = (e) => {
    e.preventDefault();
    onGuardar({
      ...form,
      area_hectareas: form.area_hectareas ? parseFloat(form.area_hectareas) : undefined,
    });
  };

  return (
    <form onSubmit={enviar} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <Campo label="Nombre del cultivo" name="nombre_cultivo" value={form.nombre_cultivo}
        onChange={cambio} required placeholder="Ej: Finca La Esperanza" />
      <Campo label="Ubicacion" name="ubicacion" value={form.ubicacion}
        onChange={cambio} placeholder="Ej: Andes, Antioquia - Coordenadas GPS" />
      <Campo label="Area (hectareas)" name="area_hectareas" value={form.area_hectareas}
        onChange={cambio} type="number" placeholder="Ej: 3.5" />
      <Campo label="Variedad de cafe" name="variedad_cafe" value={form.variedad_cafe}
        onChange={cambio} placeholder="Ej: Castillo, Caturra, Colombia" />
      <Campo label="Observaciones" name="observaciones" value={form.observaciones}
        onChange={cambio} placeholder="Informacion adicional del cultivo" />
      <div style={{ display: "flex", gap: "0.8rem", justifyContent: "flex-end", marginTop: "0.5rem" }}>
        <Boton variante="secundario" onClick={onCancelar}>Cancelar</Boton>
        <Boton tipo="submit" variante="primario">Guardar</Boton>
      </div>
    </form>
  );
}

// ==============================================================
// FORMULARIO LOTE
// ==============================================================

function FormularioLote({ onGuardar, onCancelar }) {
  const [form, setForm] = useState({
    codigo_lote:   "",
    cantidad_kg:   "",
    fecha_cosecha: "",  // F-C03 FIX
    observaciones: "",
  });

  const cambio = (e) => setForm(p => ({ ...p, [e.target.name]: e.target.value }));

  const enviar = (e) => {
    e.preventDefault();
    onGuardar({
      ...form,
      codigo_lote:   form.codigo_lote.toUpperCase(),
      cantidad_kg:   form.cantidad_kg ? parseFloat(form.cantidad_kg) : undefined,
      // F-C03 FIX: enviar fecha como ISO con T12:00:00 para evitar desfase UTC (BUG-033)
      fecha_cosecha: form.fecha_cosecha
        ? new Date(form.fecha_cosecha + "T12:00:00").toISOString()
        : undefined,
    });
  };

  return (
    <form onSubmit={enviar} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <Campo label="Codigo del lote" name="codigo_lote" value={form.codigo_lote}
        onChange={cambio} required placeholder="Ej: LOT-2025-001" />
      <Campo label="Cantidad cosechada (kg)" name="cantidad_kg" value={form.cantidad_kg}
        onChange={cambio} type="number" placeholder="Ej: 450" />
      <Campo label="Fecha de cosecha" name="fecha_cosecha" value={form.fecha_cosecha}
        onChange={cambio} type="date" required />
      <Campo label="Observaciones" name="observaciones" value={form.observaciones}
        onChange={cambio} placeholder="Notas sobre la cosecha" />
      <div style={{ display: "flex", gap: "0.8rem", justifyContent: "flex-end", marginTop: "0.5rem" }}>
        <Boton variante="secundario" onClick={onCancelar}>Cancelar</Boton>
        <Boton tipo="submit" variante="primario">Registrar Lote</Boton>
      </div>
    </form>
  );
}

// ==============================================================
// VISTA PRINCIPAL
// ==============================================================

export default function Cultivos() {
  const [resumen,        setResumen]        = useState(null);
  const [cultivos,       setCultivos]       = useState([]);
  const [lotes,          setLotes]          = useState([]);
  const [cultivoActivo,  setCultivoActivo]  = useState(null);
  const [cargando,       setCargando]       = useState(true);
  const [error,          setError]          = useState("");
  const [modalCultivo,   setModalCultivo]   = useState(false);
  const [modalLote,      setModalLote]      = useState(false);
  const [editando,       setEditando]       = useState(null);
  const nombreUsuario    = localStorage.getItem("nombre") || "Caficultor";

  // Carga inicial
  const cargarDatos = useCallback(async () => {
    setCargando(true);
    setError("");
    try {
      const [res, cvs] = await Promise.all([
        cultivoService.resumen(),
        cultivoService.listar(),
      ]);
      setResumen(res);
      setCultivos(cvs);
      if (cvs.length > 0 && !cultivoActivo) {
        setCultivoActivo(cvs[0]);
        sessionStorage.setItem("gv_cultivo_id",     String(cvs[0].id_cultivo));
        sessionStorage.setItem("gv_cultivo_nombre", cvs[0].nombre_cultivo);
        const ls = await loteService.listar(cvs[0].id_cultivo);
        setLotes(ls);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => { cargarDatos(); }, [cargarDatos]);

  const seleccionarCultivo = async (cultivo) => {
    setCultivoActivo(cultivo);
    // F-C01 FIX: persistir en sessionStorage para que IA y Monitoreo lo lean
    sessionStorage.setItem("gv_cultivo_id",     String(cultivo.id_cultivo));
    sessionStorage.setItem("gv_cultivo_nombre", cultivo.nombre_cultivo);
    const ls = await loteService.listar(cultivo.id_cultivo).catch(() => []);
    setLotes(ls);
  };

  const guardarCultivo = async (datos) => {
    try {
      if (editando) {
        await cultivoService.actualizar(editando.id_cultivo, datos);
      } else {
        await cultivoService.crear(datos);
      }
      setModalCultivo(false);
      setEditando(null);
      cargarDatos();
    } catch (e) {
      setError(e.message);
    }
  };

  const guardarLote = async (datos) => {
    if (!cultivoActivo) return;
    try {
      await loteService.crear(cultivoActivo.id_cultivo, datos);
      setModalLote(false);
      const ls = await loteService.listar(cultivoActivo.id_cultivo);
      setLotes(ls);
    } catch (e) {
      setError(e.message);
    }
  };

  // ==============================================================
  // RENDER
  // ==============================================================

  if (cargando) {
    return (
      <div style={estilos.contenedor}>
        <p style={{ textAlign: "center", color: COLOR.cafeCLaro, padding: "3rem" }}>
          Cargando cultivos...
        </p>
      </div>
    );
  }

  return (
    <div style={estilos.contenedor}>

      {/* Encabezado */}
      <div style={estilos.encabezado}>
        <div>
          <h1 style={estilos.titulo}>☕ Mis Cultivos</h1>
          <p style={{ margin: 0, color: "#7a5c3a" }}>Bienvenido, {nombreUsuario}</p>
        </div>
        <Boton onClick={() => { setEditando(null); setModalCultivo(true); }}>
          + Nuevo Cultivo
        </Boton>
      </div>

      {/* Error global */}
      {error && (
        <div style={estilos.alerta} role="alert">
          {error}
          <button onClick={() => setError("")} style={{ marginLeft: "1rem", cursor: "pointer" }}>
            cerrar
          </button>
        </div>
      )}

      {/* Tarjetas de resumen */}
      {resumen && (
        <div style={estilos.gridResumen}>
          <Tarjeta icono="🌱" titulo="Cultivos Activos"    valor={resumen.total_cultivos_activos} />
          <Tarjeta icono="📦" titulo="Total Lotes"         valor={resumen.total_lotes} />
          <Tarjeta icono="✅" titulo="Lotes Vendidos"      valor={resumen.lotes_vendidos}      color={COLOR.verde}   />
          <Tarjeta icono="⚠️" titulo="Lotes con Problema" valor={resumen.lotes_con_problema}   color={COLOR.rojo}    />
          <Tarjeta icono="🗺️" titulo="Area Total (ha)"    valor={resumen.area_total_hectareas.toFixed(1)} />
        </div>
      )}

      {/* Cuerpo principal: lista cultivos + detalle lotes */}
      <div style={estilos.gridPrincipal}>

        {/* Lista de cultivos */}
        <div style={estilos.panelIzq}>
          <h3 style={estilos.subtitulo}>Cultivos registrados</h3>
          {cultivos.length === 0 ? (
            <p style={{ color: "#999", fontSize: "0.9rem" }}>
              Aun no tienes cultivos registrados.
            </p>
          ) : (
            cultivos.map(c => (
              <div
                key={c.id_cultivo}
                onClick={() => seleccionarCultivo(c)}
                style={{
                  ...estilos.itemCultivo,
                  borderColor: cultivoActivo?.id_cultivo === c.id_cultivo
                    ? COLOR.cafe : COLOR.borde,
                  background: cultivoActivo?.id_cultivo === c.id_cultivo
                    ? "#f9f3ee" : "#fff",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.4rem" }}>
                  <strong style={{ color: COLOR.cafe }}>{c.nombre_cultivo}</strong>
                  <Badge estado={c.estado} mapa={ESTADO_CULTIVO} />
                </div>
                <p style={{ margin: 0, fontSize: "0.8rem", color: "#7a5c3a" }}>
                  {c.variedad_cafe || "Variedad no especificada"} -
                  {c.area_hectareas ? ` ${c.area_hectareas} ha` : " Area no definida"}
                </p>
                <p style={{ margin: "0.2rem 0 0", fontSize: "0.78rem", color: "#aaa" }}>
                  {c.ubicacion || "Ubicacion no registrada"}
                </p>
              </div>
            ))
          )}
        </div>

        {/* Detalle de lotes del cultivo seleccionado */}
        <div style={estilos.panelDer}>
          {cultivoActivo ? (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h3 style={estilos.subtitulo}>
                  Lotes de: {cultivoActivo.nombre_cultivo}
                </h3>
                <Boton onClick={() => setModalLote(true)} variante="verde">
                  + Nuevo Lote
                </Boton>
              </div>

              {lotes.length === 0 ? (
                <p style={{ color: "#999", fontSize: "0.9rem" }}>
                  Este cultivo aun no tiene lotes registrados.
                </p>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "0.8rem" }}>
                  {lotes.map(l => (
                    <div key={l.id_lote} style={estilos.itemLote}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <strong style={{ color: COLOR.cafe }}>{l.codigo_lote}</strong>
                        <Badge estado={l.estado_lote} mapa={ESTADO_LOTE} />
                      </div>
                      <div style={{ display: "flex", gap: "2rem", marginTop: "0.5rem", fontSize: "0.82rem", color: "#7a5c3a" }}>
                        <span>
                          Cosecha: {l.fecha_cosecha
                            ? new Date(l.fecha_cosecha).toLocaleDateString("es-CO")
                            : "No registrada"}
                        </span>
                        <span>
                          Cantidad: {l.cantidad_kg ? `${l.cantidad_kg} kg` : "No registrada"}
                        </span>
                      </div>
                      {l.codigo_qr && (
                        <p style={{ margin: "0.4rem 0 0", fontSize: "0.75rem", color: "#aaa" }}>
                          QR: {l.codigo_qr.substring(0, 20)}...
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div style={{ textAlign: "center", padding: "3rem", color: "#bbb" }}>
              <p style={{ fontSize: "3rem" }}>🌿</p>
              <p>Selecciona un cultivo para ver sus lotes</p>
            </div>
          )}
        </div>
      </div>

      {/* Modal - Nuevo / Editar Cultivo */}
      <Modal
        abierto={modalCultivo}
        titulo={editando ? "Editar Cultivo" : "Registrar Nuevo Cultivo"}
        onCerrar={() => { setModalCultivo(false); setEditando(null); }}
      >
        <FormularioCultivo
          inicial={editando || {}}
          onGuardar={guardarCultivo}
          onCancelar={() => { setModalCultivo(false); setEditando(null); }}
        />
      </Modal>

      {/* Modal - Nuevo Lote */}
      <Modal
        abierto={modalLote}
        titulo={`Registrar Lote en: ${cultivoActivo?.nombre_cultivo || ""}`}
        onCerrar={() => setModalLote(false)}
      >
        <FormularioLote
          onGuardar={guardarLote}
          onCancelar={() => setModalLote(false)}
        />
      </Modal>
    </div>
  );
}

// ==============================================================
// ESTILOS
// ==============================================================

const estilos = {
  contenedor: {
    minHeight:  "100vh",
    background: COLOR.gris,
    padding:    "2rem",
    fontFamily: "'Segoe UI', Roboto, sans-serif",
    color:      COLOR.texto,
  },
  encabezado: {
    display:        "flex",
    justifyContent: "space-between",
    alignItems:     "center",
    marginBottom:   "1.5rem",
  },
  titulo: {
    margin:     0,
    fontSize:   "1.8rem",
    fontWeight: 800,
    color:      COLOR.cafe,
  },
  subtitulo: {
    margin:       "0 0 1rem",
    fontSize:     "1rem",
    fontWeight:   700,
    color:        COLOR.cafe,
    borderBottom: `2px solid ${COLOR.borde}`,
    paddingBottom: "0.5rem",
  },
  gridResumen: {
    display:             "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap:                 "1rem",
    marginBottom:        "1.5rem",
  },
  gridPrincipal: {
    display:             "grid",
    gridTemplateColumns: "320px 1fr",
    gap:                 "1.5rem",
    alignItems:          "start",
  },
  panelIzq: {
    background:   "#fff",
    borderRadius: "12px",
    border:       `1px solid ${COLOR.borde}`,
    padding:      "1.5rem",
  },
  panelDer: {
    background:   "#fff",
    borderRadius: "12px",
    border:       `1px solid ${COLOR.borde}`,
    padding:      "1.5rem",
    minHeight:    "400px",
  },
  itemCultivo: {
    border:       `2px solid`,
    borderRadius: "10px",
    padding:      "1rem",
    cursor:       "pointer",
    marginBottom: "0.8rem",
    transition:   "all 0.15s",
  },
  itemLote: {
    border:       `1px solid ${COLOR.borde}`,
    borderRadius: "10px",
    padding:      "1rem",
    background:   "#fafafa",
  },
  alerta: {
    background:   "#fff1f0",
    border:       "1px solid #ffccc7",
    borderRadius: "8px",
    padding:      "0.8rem 1rem",
    color:        "#b91c1c",
    marginBottom: "1rem",
    fontSize:     "0.87rem",
  },
};
