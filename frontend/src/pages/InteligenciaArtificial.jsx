// ==============================================================
// modulo_04_ia / frontend/src/pages/InteligenciaArtificial.jsx
// Dashboard principal del Modulo de IA
//
// RF-05  Carga y analisis de imagen para enfermedades
// RF-06  Carga y analisis de imagen para plagas
// RF-07  Prediccion fitosanitaria con un clic
// RF-08  Recomendacion de riego con un clic
// RF-09  Recomendacion de fertilizacion con un clic
// RN-03  Banner de validez de datos visible siempre
// RNF-02 Interfaz para usuarios sin perfil tecnico
// RNF-07 Responsive web y movil
// ==============================================================

import { useState, useEffect, useRef } from "react";
import { iaService } from "../services/iaService";

// ── Colores GranoVital ──────────────────────────────────────
const C = {
  cafe:    "#6f3a1b", cafeCla: "#a0522d", verde:  "#2d7a3a",
  amarillo:"#c8a000", rojo:    "#b91c1c", azul:   "#0284c7",
  gris:    "#f5f0eb", borde:   "#d4b896", texto:  "#1a0e05",
};

// ── Paleta de urgencia ──────────────────────────────────────
const URGENCIA_COLOR = {
  bajo:     { bg: "#f0fdf4", borde: C.verde,    texto: C.verde    },
  medio:    { bg: "#fffbeb", borde: C.amarillo, texto: C.amarillo },
  alto:     { bg: "#fff7ed", borde: "#ea580c",  texto: "#ea580c"  },
  critico:  { bg: "#fff1f0", borde: C.rojo,     texto: C.rojo     },
  moderado: { bg: "#fffbeb", borde: C.amarillo, texto: C.amarillo },
};
const RIESGO_ICONO = { bajo:"🟢", moderado:"🟡", alto:"🟠", critico:"🔴" };

// ── Subcomponentes ───────────────────────────────────────────

function Modal({ abierto, titulo, onCerrar, children }) {
  if (!abierto) return null;
  return (
    <div style={{
      position:"fixed", inset:0, background:"rgba(0,0,0,0.45)",
      display:"flex", alignItems:"center", justifyContent:"center",
      zIndex:1000, padding:"1rem",
    }}>
      <div style={{
        background:"#fff", borderRadius:"16px", padding:"2rem",
        width:"100%", maxWidth:"580px", maxHeight:"90vh",
        overflowY:"auto", boxShadow:"0 20px 60px rgba(0,0,0,0.3)",
      }}>
        <div style={{ display:"flex", justifyContent:"space-between", marginBottom:"1.5rem" }}>
          <h3 style={{ margin:0, color:C.cafe }}>{titulo}</h3>
          <button onClick={onCerrar}
            style={{ background:"none", border:"none", fontSize:"1.4rem", cursor:"pointer" }}>✕</button>
        </div>
        {children}
      </div>
    </div>
  );
}

function Badge({ texto, urgencia = "bajo" }) {
  const col = URGENCIA_COLOR[urgencia] || URGENCIA_COLOR.bajo;
  return (
    <span style={{
      background:col.bg, border:`1.5px solid ${col.borde}`,
      color:col.texto, borderRadius:"999px",
      padding:"0.2rem 0.8rem", fontSize:"0.78rem", fontWeight:700,
    }}>
      {texto}
    </span>
  );
}

function BannerRN03({ validez }) {
  if (!validez) return null;
  const ok = validez.datos_validos_rn03;
  return (
    <div style={{
      background: ok ? "#f0fdf4" : "#fffbeb",
      border:`1.5px solid ${ok ? C.verde : C.amarillo}`,
      borderRadius:"12px", padding:"1rem 1.4rem",
      display:"flex", alignItems:"center", gap:"0.8rem",
    }}>
      <span style={{ fontSize:"1.5rem" }}>{ok ? "✅" : "⚠️"}</span>
      <div>
        <p style={{ margin:0, fontWeight:700, color: ok ? C.verde : C.amarillo }}>
          {ok ? "Datos actualizados — IA completamente disponible"
               : "Datos desactualizados — IA limitada (RN-03)"}
        </p>
        <p style={{ margin:"0.2rem 0 0", fontSize:"0.83rem", color:"#7a5c3a" }}>
          {validez.mensaje_rn03}
        </p>
      </div>
    </div>
  );
}

// F-I01 FIX: Banner prominente cuando los diagnósticos de imagen son simulados
function BannerModoSimulado({ resultado }) {
  if (!resultado || !resultado.modo_simulado) return null;
  return (
    <div style={{
      background: "#fff1f0",
      border: "2px solid #ff4d4f",
      borderRadius: "12px",
      padding: "1rem 1.4rem",
      display: "flex", alignItems: "flex-start", gap: "0.8rem",
      marginBottom: "0.5rem",
    }}>
      <span style={{ fontSize: "1.6rem", lineHeight: 1 }}>⚠️</span>
      <div>
        <p style={{ margin: 0, fontWeight: 800, color: "#cf1322", fontSize: "0.95rem" }}>
          MODO DEMOSTRACIÓN — Diagnósticos NO reales
        </p>
        <p style={{ margin: "0.3rem 0 0", fontSize: "0.82rem", color: "#7a5c3a", lineHeight: 1.5 }}>
          Los modelos de IA (CNN) no están instalados. Este resultado fue generado
          automáticamente y <strong>no corresponde a la imagen real analizada</strong>.
          No tome decisiones agronómicas basadas en este diagnóstico.
        </p>
      </div>
    </div>
  );
}

function TarjetaResultado({ titulo, icono, datos, cargando, error, onAccion, textoAccion, urgencia }) {
  const col = URGENCIA_COLOR[urgencia] || { bg:"#fff", borde:C.borde };
  return (
    <div style={{
      background:col.bg, border:`1.5px solid ${col.borde}`,
      borderRadius:"14px", padding:"1.2rem 1.4rem",
    }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:"0.8rem" }}>
        <h3 style={{ margin:0, fontSize:"1rem", color:C.cafe }}>
          {icono} {titulo}
        </h3>
        {onAccion && (
          <button onClick={onAccion} disabled={cargando}
            style={{
              padding:"0.45rem 1rem", borderRadius:"8px", border:"none",
              background: cargando ? "#c9a88a" : C.cafe,
              color:"#fff", fontWeight:700, cursor: cargando ? "not-allowed" : "pointer",
              fontSize:"0.82rem",
            }}>
            {cargando ? "Analizando..." : textoAccion || "Ejecutar"}
          </button>
        )}
      </div>

      {error && (
        <div style={{
          background:"#fff1f0", border:"1px solid #ffccc7",
          borderRadius:"8px", padding:"0.6rem", color:C.rojo,
          fontSize:"0.83rem", marginBottom:"0.6rem",
        }}>
          {error}
        </div>
      )}

      {datos && (
        <div style={{ fontSize:"0.88rem", lineHeight:1.6 }}>
          {datos}
        </div>
      )}

      {!datos && !cargando && !error && (
        <p style={{ color:"#bbb", fontSize:"0.85rem", margin:0 }}>
          Sin resultados aun. Ejecute el analisis.
        </p>
      )}
    </div>
  );
}

// ── Panel de imagen para RF-05 / RF-06 ───────────────────────

function PanelImagen({ tipo, cultivoId, onResultado }) {
  const [archivo,   setArchivo]   = useState(null);
  const [preview,   setPreview]   = useState(null);
  const [cargando,  setCargando]  = useState(false);
  const [error,     setError]     = useState("");
  const [resultado, setResultado] = useState(null);
  const inputRef = useRef();

  const seleccionar = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    setArchivo(f);
    setPreview(URL.createObjectURL(f));
    setResultado(null);
    setError("");
  };

  const analizar = async () => {
    if (!archivo) return;
    setCargando(true);
    setError("");
    try {
      const fn   = tipo === "enfermedad"
        ? iaService.analizarEnfermedad
        : iaService.analizarPlaga;
      const res  = await fn(cultivoId, archivo);
      setResultado(res);
      onResultado && onResultado(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  };

  const col = resultado ? (URGENCIA_COLOR[resultado.nivel_urgencia] || URGENCIA_COLOR.bajo) : null;

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:"1rem" }}>
      {/* Zona de carga */}
      <div
        onClick={() => inputRef.current.click()}
        style={{
          border:`2px dashed ${C.borde}`, borderRadius:"12px",
          padding:"2rem", textAlign:"center", cursor:"pointer",
          background: preview ? "#000" : C.gris,
          position:"relative", overflow:"hidden", minHeight:"180px",
          display:"flex", alignItems:"center", justifyContent:"center",
        }}
      >
        {preview
          ? <img src={preview} alt="preview"
              style={{ maxWidth:"100%", maxHeight:"250px", borderRadius:"8px" }} />
          : <div>
              <p style={{ fontSize:"2.5rem", margin:"0 0 0.5rem" }}>📷</p>
              <p style={{ margin:0, color:C.cafeCla, fontWeight:600 }}>
                Haga clic para seleccionar imagen
              </p>
              <p style={{ margin:0, fontSize:"0.78rem", color:"#9a7a5a" }}>
                JPG, PNG o WEBP — max 10 MB
              </p>
            </div>
        }
        <input ref={inputRef} type="file" accept="image/*"
          onChange={seleccionar} style={{ display:"none" }} />
      </div>

      {archivo && (
        <button onClick={analizar} disabled={cargando}
          style={{
            padding:"0.75rem", borderRadius:"10px", border:"none",
            background: cargando ? "#c9a88a"
              : "linear-gradient(135deg, #6f3a1b, #a0522d)",
            color:"#fff", fontWeight:800, fontSize:"1rem",
            cursor: cargando ? "not-allowed" : "pointer",
          }}>
          {cargando ? "⏳ Analizando imagen..." : "🔬 Analizar imagen"}
        </button>
      )}

      {error && (
        <div style={{
          background:"#fff1f0", border:"1px solid #ffccc7",
          borderRadius:"8px", padding:"0.8rem", color:C.rojo,
        }}>{error}</div>
      )}

      {resultado && (
        <BannerModoSimulado resultado={resultado} />
      )}

      {resultado && col && (
        <div style={{
          background:col.bg, border:`2px solid ${col.borde}`,
          borderRadius:"12px", padding:"1.2rem",
        }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
            <h4 style={{ margin:0, color:col.texto }}>{resultado.diagnostico}</h4>
            <Badge texto={resultado.nivel_urgencia.toUpperCase()} urgencia={resultado.nivel_urgencia} />
          </div>
          <p style={{ margin:"0.4rem 0", fontSize:"0.85rem", color:"#7a5c3a" }}>
            Confianza: <strong>{resultado.confianza_pct}</strong>
            {" · "}{resultado.tiempo_pct_rnf01}
          </p>

          {/* Top clases */}
          <div style={{ margin:"0.8rem 0", display:"flex", gap:"0.5rem", flexWrap:"wrap" }}>
            {resultado.top_clases.map(c => (
              <span key={c.clase} style={{
                background:"rgba(0,0,0,0.06)", borderRadius:"6px",
                padding:"0.2rem 0.6rem", fontSize:"0.78rem",
              }}>
                {c.clase} {(c.probabilidad * 100).toFixed(0)}%
              </span>
            ))}
          </div>

          <hr style={{ border:"none", borderTop:`1px solid ${col.borde}`, margin:"0.8rem 0" }} />
          <p style={{ margin:0, fontSize:"0.85rem", lineHeight:1.7 }}>
            <strong>Recomendacion:</strong><br />{resultado.recomendacion}
          </p>
        </div>
      )}
    </div>
  );
}

// ── Componente principal ─────────────────────────────────────

export default function InteligenciaArtificial() {
  const cultivoId = 1;
  const [resumen,  setResumen]  = useState(null);
  const [cargando, setCargando] = useState(true);

  // Estados de cada modelo
  const [fito,    setFito]    = useState(null);
  const [riego,   setRiego]   = useState(null);
  const [fert,    setFert]    = useState(null);
  const [loadF,   setLoadF]   = useState(false);
  const [loadR,   setLoadR]   = useState(false);
  const [loadFe,  setLoadFe]  = useState(false);
  const [errF,    setErrF]    = useState("");
  const [errR,    setErrR]    = useState("");
  const [errFe,   setErrFe]   = useState("");

  const [tabActiva, setTabActiva] = useState("enfermedades");

  useEffect(() => {
    iaService.resumen(cultivoId)
      .then(setResumen)
      .catch(() => {})
      .finally(() => setCargando(false));
  }, []);

  const ejecutarFito = async () => {
    setLoadF(true); setErrF("");
    try { setFito(await iaService.predecirFitosanitario(cultivoId)); }
    catch(e) { setErrF(e.message); }
    finally { setLoadF(false); }
  };

  const ejecutarRiego = async () => {
    setLoadR(true); setErrR("");
    try { setRiego(await iaService.recomendarRiego(cultivoId)); }
    catch(e) { setErrR(e.message); }
    finally { setLoadR(false); }
  };

  const ejecutarFert = async () => {
    setLoadFe(true); setErrFe("");
    try { setFert(await iaService.recomendarFertilizacion(cultivoId)); }
    catch(e) { setErrFe(e.message); }
    finally { setLoadFe(false); }
  };

  // ── Renderizado de cada resultado ──────────────────────────

  const datosFito = fito && (
    <div>
      <p style={{ margin:"0 0 0.4rem" }}>
        {RIESGO_ICONO[fito.nivel_riesgo]} Nivel de riesgo:{" "}
        <strong>{fito.nivel_riesgo.toUpperCase()}</strong> — {fito.probabilidad_pct}
      </p>
      {fito.factores_riesgo.map((f, i) => (
        <p key={i} style={{ margin:"0.15rem 0", fontSize:"0.82rem", color:"#7a5c3a" }}>
          · {f}
        </p>
      ))}
      <hr style={{ border:"none", borderTop:`1px solid ${C.borde}`, margin:"0.8rem 0" }} />
      <p style={{ margin:0 }}><strong>Recomendacion:</strong><br />{fito.recomendacion}</p>
    </div>
  );

  const datosRiego = riego && (
    <div>
      <p style={{ margin:"0 0 0.4rem" }}>
        Necesita riego:{" "}
        <strong style={{ color: riego.necesita_riego === "si" ? C.rojo : C.verde }}>
          {riego.necesita_riego.toUpperCase()}
        </strong>
        {riego.cantidad_litros_m2 && ` — ${riego.cantidad_litros_m2} L/m²`}
        {riego.frecuencia_dias    && ` — cada ${riego.frecuencia_dias} dia(s)`}
      </p>
      <p style={{ margin:"0.3rem 0", fontSize:"0.82rem", color:"#7a5c3a" }}>
        {riego.justificacion}
      </p>
      <hr style={{ border:"none", borderTop:`1px solid ${C.borde}`, margin:"0.8rem 0" }} />
      <p style={{ margin:0 }}><strong>Accion:</strong><br />{riego.recomendacion}</p>
    </div>
  );

  const datosFert = fert && (
    <div>
      <p style={{ margin:"0 0 0.4rem" }}>
        Fertilizante: <strong>{fert.tipo_fertilizante}</strong>
      </p>
      {fert.dosis_kg_ha && (
        <p style={{ margin:"0 0 0.25rem", fontSize:"0.83rem" }}>
          Dosis: {fert.dosis_kg_ha} kg/ha · {fert.frecuencia_aplicacion}
        </p>
      )}
      {fert.nutrientes_deficientes.length > 0 && (
        <p style={{ margin:"0 0 0.5rem", fontSize:"0.82rem", color:"#7a5c3a" }}>
          Deficiencias: {fert.nutrientes_deficientes.join(", ")}
        </p>
      )}
      <hr style={{ border:"none", borderTop:`1px solid ${C.borde}`, margin:"0.8rem 0" }} />
      <p style={{ margin:0 }}><strong>Plan:</strong><br />{fert.recomendacion}</p>
    </div>
  );

  if (cargando) return (
    <div style={estilos.contenedor}>
      <p style={{ textAlign:"center", color:C.cafeCla, padding:"3rem" }}>
        Cargando modulo de IA...
      </p>
    </div>
  );

  // ── Render principal ───────────────────────────────────────
  const TABS = [
    { id:"enfermedades",   label:"🍃 Enfermedades" },
    { id:"plagas",         label:"🐛 Plagas"        },
    { id:"prediccion",     label:"🌦️ Riesgo"        },
    { id:"riego",          label:"💧 Riego"         },
    { id:"fertilizacion",  label:"🌿 Fertilización" },
  ];

  return (
    <div style={estilos.contenedor}>
      {/* Encabezado */}
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center" }}>
        <div>
          <h1 style={{ margin:0, fontSize:"1.8rem", fontWeight:800, color:C.cafe }}>
            🤖 Inteligencia Artificial
          </h1>
          <p style={{ margin:0, color:"#7a5c3a" }}>GranoVital IA — Cultivo #{cultivoId}</p>
        </div>
      </div>

      {/* Banner RN-03 */}
      <BannerRN03 validez={resumen} />

      {/* Alertas del resumen */}
      {resumen?.alertas?.length > 0 && (
        <div style={{
          background:"#fff7ed", border:`1px solid #ea580c`,
          borderRadius:"12px", padding:"1rem 1.4rem",
        }}>
          <p style={{ margin:"0 0 0.5rem", fontWeight:700, color:"#ea580c" }}>
            Alertas activas ({resumen.alertas.length})
          </p>
          {resumen.alertas.map((a, i) => (
            <p key={i} style={{ margin:"0.2rem 0", fontSize:"0.85rem", color:"#7a5c3a" }}>
              ⚠ {a}
            </p>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div style={{
        display:"flex", gap:0,
        borderBottom:`2px solid ${C.borde}`,
        overflowX:"auto",
      }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTabActiva(t.id)}
            style={{
              padding:"0.6rem 1.2rem", border:"none", background:"none",
              fontWeight: tabActiva === t.id ? 800 : 400,
              color:      tabActiva === t.id ? C.cafe : "#9a7a5a",
              borderBottom: tabActiva === t.id
                ? `3px solid ${C.cafe}` : "3px solid transparent",
              cursor:"pointer", fontSize:"0.88rem",
              marginBottom:"-2px", whiteSpace:"nowrap",
            }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Contenido de cada tab */}
      <div style={{ minHeight:"300px" }}>
        {tabActiva === "enfermedades" && (
          <div>
            <p style={{ color:"#7a5c3a", fontSize:"0.88rem", marginBottom:"1rem" }}>
              RF-05: suba una foto de una hoja de cafe para detectar Roya,
              Mancha de Hierro, Antracnosis o CBD.
            </p>
            <PanelImagen tipo="enfermedad" cultivoId={cultivoId} />
          </div>
        )}

        {tabActiva === "plagas" && (
          <div>
            <p style={{ color:"#7a5c3a", fontSize:"0.88rem", marginBottom:"1rem" }}>
              RF-06: suba una foto del cultivo o fruto para identificar Broca,
              Minador de la Hoja, Trips o Acaro Rojo.
            </p>
            <PanelImagen tipo="plaga" cultivoId={cultivoId} />
          </div>
        )}

        {tabActiva === "prediccion" && (
          <TarjetaResultado
            titulo="Prediccion de Riesgo Fitosanitario"
            icono="🌦️"
            datos={datosFito}
            cargando={loadF}
            error={errF}
            urgencia={fito?.nivel_riesgo}
            onAccion={ejecutarFito}
            textoAccion="Predecir riesgo ahora"
          />
        )}

        {tabActiva === "riego" && (
          <TarjetaResultado
            titulo="Recomendacion de Riego"
            icono="💧"
            datos={datosRiego}
            cargando={loadR}
            error={errR}
            urgencia={riego?.nivel_urgencia}
            onAccion={ejecutarRiego}
            textoAccion="Evaluar necesidad de riego"
          />
        )}

        {tabActiva === "fertilizacion" && (
          <TarjetaResultado
            titulo="Plan de Fertilizacion"
            icono="🌿"
            datos={datosFert}
            cargando={loadFe}
            error={errFe}
            urgencia={fert?.nivel_urgencia}
            onAccion={ejecutarFert}
            textoAccion="Generar plan de fertilizacion"
          />
        )}
      </div>
    </div>
  );
}

const estilos = {
  contenedor: {
    minHeight:"100vh", background:C.gris, padding:"2rem",
    fontFamily:"'Segoe UI', Roboto, sans-serif", color:C.texto,
    display:"flex", flexDirection:"column", gap:"1.5rem",
  },
};
