// ==============================================================
// frontend/src/pages/Cultivos.jsx
// Vista principal de Gestión de Cultivos y Lotes
// RF-03 Cultivos | RF-04 Lotes | RNF-02 Usabilidad
// RNF-07 Funciona en web y móvil (responsive)
//
// QA FIXES aplicados sobre la versión original del proyecto:
//   BUG-011 FIX (original): sessionStorage para cultivoId activo
//   BUG-026 FIX (original): fecha_cosecha sin conversión UTC errónea
//   DATA-003 FIX: anti-doble-envío con useRef en todos los formularios
//   DATA-004 FIX: validación de formato código de lote (LETRAS-AÑO-NUM)
//   DATA-008 FIX: maxLength con contador en nombre_cultivo
//   UX-001 FIX:  Modal compartido con cierre por tecla Escape (WCAG 2.1)
//   UX-002 FIX:  aria-label descriptivo en botón cerrar modal
//   SEC-006 FIX: nombreUsuario desde AuthContext, no desde localStorage
// ==============================================================

import { useState, useEffect, useCallback, useRef } from "react";
import { cultivoService, loteService } from "../services/cultivoService";
import Modal from "../components/Modal";
import { useAuth } from "../components/AuthContext";

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

const ESTADO_CULTIVO = {
  creado:                 { texto: "Creado",          color: COLOR.amarillo },
  en_seguimiento:         { texto: "En Seguimiento",  color: COLOR.verde    },
  con_problema_detectado: { texto: "Con Problema",    color: COLOR.rojo     },
  tratamiento_aplicado:   { texto: "En Tratamiento",  color: "#7c3aed"      },
  finalizado:             { texto: "Finalizado",      color: "#64748b"      },
  eliminado:              { texto: "Eliminado",       color: "#94a3b8"      },
};

const ESTADO_LOTE = {
  registrado:   { texto: "Registrado",   color: COLOR.amarillo },
  disponible:   { texto: "Disponible",   color: "#0284c7"      },
  en_analisis:  { texto: "En Análisis",  color: "#7c3aed"      },
  aprobado:     { texto: "Aprobado",     color: COLOR.verde    },
  con_problema: { texto: "Con Problema", color: COLOR.rojo     },
  vendido:      { texto: "Vendido",      color: "#64748b"      },
  eliminado:    { texto: "Eliminado",    color: "#94a3b8"      },
};

// DATA-004 FIX: regex para validar formato del código de lote
const REGEX_CODIGO_LOTE = /^[A-Z]{2,10}-\d{4}-\d{1,6}$/;

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

// DATA-008 FIX: campo con maxLength y contador de caracteres
function Campo({ label, name, value, onChange, type = "text", required = false,
  placeholder = "", maxLength, errorMsg = "" }) {
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
        maxLength={maxLength}
        style={{
          padding:      "0.6rem 0.9rem",
          border:       `1.5px solid ${errorMsg ? COLOR.rojo : COLOR.borde}`,
          borderRadius: "8px",
          fontSize:     "0.9rem",
          outline:      "none",
        }}
      />
      {/* DATA-008 FIX: contador visible de caracteres */}
      {maxLength && (
        <span style={{
          fontSize: "0.73rem", textAlign: "right",
          color: value.length > maxLength * 0.9 ? COLOR.amarillo : "#9a7a5a",
        }}>
          {value.length} / {maxLength}
        </span>
      )}
      {errorMsg && (
        <span style={{ fontSize: "0.73rem", color: COLOR.rojo }} role="alert">{errorMsg}</span>
      )}
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
    primario:   { background: COLOR.cafe,  color: "#fff"     },
    secundario: { background: "#f5f0eb",   color: COLOR.cafe, border: `1px solid ${COLOR.borde}` },
    peligro:    { background: "#fee2e2",   color: COLOR.rojo  },
    verde:      { background: "#dcfce7",   color: COLOR.verde },
  };

  return (
    <button
      type={tipo}
      onClick={onClick}
      disabled={desactivado}
      aria-disabled={desactivado}
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
  // DATA-003 FIX: anti-doble-envío
  const [guardando, setGuardando] = useState(false);
  const enviandoRef = useRef(false);

  const cambio = (e) => setForm(p => ({ ...p, [e.target.name]: e.target.value }));

  const enviar = async (e) => {
    e.preventDefault();
    if (enviandoRef.current) return;
    enviandoRef.current = true;
    setGuardando(true);
    try {
      await onGuardar({
        ...form,
        area_hectareas: form.area_hectareas ? parseFloat(form.area_hectareas) : undefined,
      });
    } finally {
      enviandoRef.current = false;
      setGuardando(false);
    }
  };

  return (
    <form onSubmit={enviar} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <Campo label="Nombre del cultivo" name="nombre_cultivo" value={form.nombre_cultivo}
        onChange={cambio} required placeholder="Ej: Finca La Esperanza" maxLength={100} />
      <Campo label="Ubicación" name="ubicacion" value={form.ubicacion}
        onChange={cambio} placeholder="Ej: Andes, Antioquia - Coordenadas GPS" maxLength={200} />
      <Campo label="Área (hectáreas)" name="area_hectareas" value={form.area_hectareas}
        onChange={cambio} type="number" placeholder="Ej: 3.5" />
      <Campo label="Variedad de café" name="variedad_cafe" value={form.variedad_cafe}
        onChange={cambio} placeholder="Ej: Castillo, Caturra, Colombia" maxLength={80} />
      <Campo label="Observaciones" name="observaciones" value={form.observaciones}
        onChange={cambio} placeholder="Información adicional del cultivo" maxLength={500} />
      <div style={{ display: "flex", gap: "0.8rem", justifyContent: "flex-end", marginTop: "0.5rem" }}>
        <Boton variante="secundario" onClick={onCancelar} desactivado={guardando}>Cancelar</Boton>
        <Boton tipo="submit" variante="primario" desactivado={guardando}>
          {guardando ? "Guardando..." : "Guardar"}
        </Boton>
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
    fecha_cosecha: "",
    observaciones: "",
  });
  const [errores,   setErrores]  = useState({});
  const [guardando, setGuardando] = useState(false);
  const enviandoRef = useRef(false); // DATA-003

  const cambio = (e) => {
    setForm(p => ({ ...p, [e.target.name]: e.target.value }));
    if (errores[e.target.name]) setErrores(p => ({ ...p, [e.target.name]: "" }));
  };

  // DATA-004 FIX: validar formato del código de lote
  const validar = () => {
    const nuevos = {};
    const codigo = form.codigo_lote.trim().toUpperCase();
    if (!codigo) {
      nuevos.codigo_lote = "El código de lote es obligatorio.";
    } else if (!REGEX_CODIGO_LOTE.test(codigo)) {
      nuevos.codigo_lote = "Formato inválido. Usa: LETRAS-AÑO-NÚMERO (Ej: LOT-2025-001)";
    }
    setErrores(nuevos);
    return Object.keys(nuevos).length === 0;
  };

  const enviar = async (e) => {
    e.preventDefault();
    if (!validar()) return;
    if (enviandoRef.current) return; // DATA-003
    enviandoRef.current = true;
    setGuardando(true);
    try {
      await onGuardar({
        ...form,
        codigo_lote: form.codigo_lote.toUpperCase(),
        cantidad_kg: form.cantidad_kg ? parseFloat(form.cantidad_kg) : undefined,
        // BUG-026 FIX (original): enviar fecha como YYYY-MM-DD sin conversión UTC
        // new Date().toISOString() desplaza el día al enviar en zonas horarias negativas
        fecha_cosecha: form.fecha_cosecha || undefined,
      });
    } finally {
      enviandoRef.current = false;
      setGuardando(false);
    }
  };

  return (
    <form onSubmit={enviar} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <Campo label="Código del lote" name="codigo_lote" value={form.codigo_lote}
        onChange={cambio} required placeholder="Ej: LOT-2025-001"
        errorMsg={errores.codigo_lote} />
      {/* DATA-004 FIX: texto de ayuda del formato */}
      {!errores.codigo_lote && (
        <p style={{ margin: "-0.7rem 0 0", fontSize: "0.73rem", color: "#9a7a5a" }}>
          Formato: LETRAS-AÑO-NÚMERO (ej: LOT-2025-001, CAFE-2025-042)
        </p>
      )}
      <Campo label="Cantidad cosechada (kg)" name="cantidad_kg" value={form.cantidad_kg}
        onChange={cambio} type="number" placeholder="Ej: 450" />
      <Campo label="Fecha de cosecha" name="fecha_cosecha" value={form.fecha_cosecha}
        onChange={cambio} type="date" />
      <Campo label="Observaciones" name="observaciones" value={form.observaciones}
        onChange={cambio} placeholder="Notas sobre la cosecha" maxLength={300} />
      <div style={{ display: "flex", gap: "0.8rem", justifyContent: "flex-end", marginTop: "0.5rem" }}>
        <Boton variante="secundario" onClick={onCancelar} desactivado={guardando}>Cancelar</Boton>
        <Boton tipo="submit" variante="primario" desactivado={guardando}>
          {guardando ? "Registrando..." : "Registrar Lote"}
        </Boton>
      </div>
    </form>
  );
}

// ==============================================================
// VISTA PRINCIPAL
// ==============================================================

export default function Cultivos() {
  // SEC-006 FIX: nombre desde AuthContext, no desde localStorage
  const { usuario } = useAuth();
  const nombreUsuario = usuario?.nombre || "Caficultor";

  const [resumen,       setResumen]       = useState(null);
  const [cultivos,      setCultivos]      = useState([]);
  const [lotes,         setLotes]         = useState([]);
  const [cultivoActivo, setCultivoActivo] = useState(null);
  const [cargando,      setCargando]      = useState(true);
  const [error,         setError]         = useState("");
  const [modalCultivo,  setModalCultivo]  = useState(false);
  const [modalLote,     setModalLote]     = useState(false);
  const [editando,      setEditando]      = useState(null);

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
        // BUG-011 FIX (original): persistir cultivoId para Monitoreo e IA
        sessionStorage.setItem("gv_cultivo_activo", cvs[0].id_cultivo);
        sessionStorage.setItem("gv_cultivo_nombre", cvs[0].nombre_cultivo);
        const ls = await loteService.listar(cvs[0].id_cultivo);
        setLotes(ls);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { cargarDatos(); }, [cargarDatos]);

  const seleccionarCultivo = async (cultivo) => {
    setCultivoActivo(cultivo);
    // BUG-011 FIX (original): actualizar sessionStorage al cambiar de cultivo activo
    sessionStorage.setItem("gv_cultivo_activo", cultivo.id_cultivo);
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
      throw e;
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
      throw e;
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

      <div style={estilos.encabezado}>
        <div>
          <h1 style={estilos.titulo}>☕ Mis Cultivos</h1>
          <p style={{ margin: 0, color: "#7a5c3a" }}>Bienvenido, {nombreUsuario}</p>
        </div>
        <Boton onClick={() => { setEditando(null); setModalCultivo(true); }}>
          + Nuevo Cultivo
        </Boton>
      </div>

      {error && (
        <div style={estilos.alerta} role="alert">
          {error}
          <button onClick={() => setError("")}
            style={{ marginLeft: "1rem", cursor: "pointer", fontWeight: 700, background: "none", border: "none", color: "#b91c1c" }}>
            ✕
          </button>
        </div>
      )}

      {resumen && (
        <div style={estilos.gridResumen}>
          <Tarjeta icono="🌱" titulo="Cultivos Activos"   valor={resumen.total_cultivos_activos} />
          <Tarjeta icono="📦" titulo="Total Lotes"        valor={resumen.total_lotes} />
          <Tarjeta icono="✅" titulo="Lotes Vendidos"     valor={resumen.lotes_vendidos}     color={COLOR.verde}  />
          <Tarjeta icono="⚠️" titulo="Lotes con Problema" valor={resumen.lotes_con_problema}  color={COLOR.rojo}   />
          <Tarjeta icono="🗺️" titulo="Área Total (ha)"   valor={(resumen.area_total_hectareas || 0).toFixed(1)} />
        </div>
      )}

      <div style={estilos.gridPrincipal}>

        {/* Lista de cultivos */}
        <div style={estilos.panelIzq}>
          <h3 style={estilos.subtitulo}>Cultivos registrados</h3>
          {cultivos.length === 0 ? (
            <p style={{ color: "#999", fontSize: "0.9rem" }}>
              Aún no tienes cultivos registrados.
            </p>
          ) : (
            cultivos.map(c => (
              <div
                key={c.id_cultivo}
                onClick={() => seleccionarCultivo(c)}
                role="button"
                tabIndex={0}
                aria-pressed={cultivoActivo?.id_cultivo === c.id_cultivo}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") seleccionarCultivo(c); }}
                style={{
                  ...estilos.itemCultivo,
                  borderColor: cultivoActivo?.id_cultivo === c.id_cultivo ? COLOR.cafe : COLOR.borde,
                  background:  cultivoActivo?.id_cultivo === c.id_cultivo ? "#f9f3ee" : "#fff",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.4rem" }}>
                  <strong style={{ color: COLOR.cafe }}>{c.nombre_cultivo}</strong>
                  <Badge estado={c.estado} mapa={ESTADO_CULTIVO} />
                </div>
                <p style={{ margin: 0, fontSize: "0.8rem", color: "#7a5c3a" }}>
                  {c.variedad_cafe || "Variedad no especificada"} —
                  {c.area_hectareas ? ` ${c.area_hectareas} ha` : " Área no definida"}
                </p>
                <p style={{ margin: "0.2rem 0 0", fontSize: "0.78rem", color: "#aaa" }}>
                  {c.ubicacion || "Ubicación no registrada"}
                </p>
              </div>
            ))
          )}
        </div>

        {/* Detalle de lotes */}
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
                  Este cultivo aún no tiene lotes registrados.
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
                            // BUG-026 FIX: evitar desplazamiento de zona horaria al mostrar
                            ? new Date(l.fecha_cosecha + "T12:00:00").toLocaleDateString("es-CO")
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

      {/* UX-001/002 FIX: Modal compartido (Escape + aria-label) */}
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
    margin: 0, fontSize: "1.8rem",
    fontWeight: 800, color: COLOR.cafe,
  },
  subtitulo: {
    margin: "0 0 1rem",
    fontSize: "1rem",
    fontWeight: 700,
    color: COLOR.cafe,
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
    border:       "2px solid",
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
    display:      "flex",
    alignItems:   "center",
  },
};
