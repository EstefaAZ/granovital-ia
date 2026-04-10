// ==============================================================
// modulo_03_monitoreo / frontend/src/pages/Monitoreo.jsx
// Dashboard de Monitoreo Ambiental y Suelo
//
// RF-03  Visualiza variables ambientales en tiempo real
// RF-04  Visualiza estado del suelo con interpretacion
// RN-03  Indicador de validez de datos para IA
// RNF-02 Usabilidad para usuarios sin perfil tecnico
// RNF-07 Responsive - funciona en web y movil
// ==============================================================

import { useState } from "react";
import { useMonitoreo, useHistorialAmbiental, useHistorialSuelo } from "../hooks/useMonitoreo";
import FormularioAmbiental from "../components/FormularioAmbiental";
import FormularioSuelo     from "../components/FormularioSuelo";

// ==============================================================
// CONSTANTES DE DISENO
// ==============================================================
const COLOR = {
  cafe:     "#6f3a1b",
  cafeCla:  "#a0522d",
  verde:    "#2d7a3a",
  amarillo: "#c8a000",
  rojo:     "#b91c1c",
  azul:     "#0284c7",
  gris:     "#f5f0eb",
  borde:    "#d4b896",
  texto:    "#1a0e05",
};

// ==============================================================
// SUBCOMPONENTES
// ==============================================================

function Modal({ abierto, titulo, onCerrar, children }) {
  if (!abierto) return null;
  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)",
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 1000, padding: "1rem",
    }}>
      <div style={{
        background: "#fff", borderRadius: "16px", padding: "2rem",
        width: "100%", maxWidth: "540px", maxHeight: "90vh",
        overflowY: "auto", boxShadow: "0 20px 60px rgba(0,0,0,0.3)",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "1.5rem" }}>
          <h3 style={{ margin: 0, color: COLOR.cafe }}>{titulo}</h3>
          <button onClick={onCerrar}
            style={{ background: "none", border: "none", fontSize: "1.4rem", cursor: "pointer" }}>
            x
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function TarjetaMetrica({ icono, etiqueta, valor, unidad, estado = "normal" }) {
  const colores = {
    normal:   { bg: "#fff",     borde: COLOR.borde,   texto: COLOR.cafe  },
    alerta:   { bg: "#fffbeb",  borde: COLOR.amarillo, texto: COLOR.amarillo },
    critico:  { bg: "#fff1f0",  borde: COLOR.rojo,    texto: COLOR.rojo  },
    optimo:   { bg: "#f0fdf4",  borde: COLOR.verde,   texto: COLOR.verde },
  };
  const c = colores[estado] || colores.normal;
  return (
    <div style={{
      background: c.bg, border: `1.5px solid ${c.borde}`,
      borderRadius: "12px", padding: "1rem 1.2rem",
      display: "flex", alignItems: "center", gap: "0.8rem",
    }}>
      <span style={{ fontSize: "1.8rem" }}>{icono}</span>
      <div>
        <p style={{ margin: 0, fontSize: "0.78rem", color: "#7a5c3a", fontWeight: 600 }}>
          {etiqueta}
        </p>
        <p style={{ margin: 0, fontSize: "1.5rem", fontWeight: 800, color: c.texto }}>
          {valor !== null && valor !== undefined ? `${valor}` : "-"}
          {valor !== null && valor !== undefined && unidad && (
            <span style={{ fontSize: "0.85rem", fontWeight: 400 }}> {unidad}</span>
          )}
        </p>
      </div>
    </div>
  );
}

function BannerValidez({ validez }) {
  if (!validez) return null;
  const esValido = validez.ambos_validos;
  return (
    <div style={{
      background:   esValido ? "#f0fdf4" : "#fffbeb",
      border:       `1.5px solid ${esValido ? COLOR.verde : COLOR.amarillo}`,
      borderRadius: "12px",
      padding:      "1rem 1.4rem",
      display:      "flex",
      alignItems:   "center",
      gap:          "0.8rem",
    }}>
      <span style={{ fontSize: "1.5rem" }}>{esValido ? "✅" : "⚠️"}</span>
      <div>
        <p style={{ margin: 0, fontWeight: 700, color: esValido ? COLOR.verde : COLOR.amarillo }}>
          {esValido
            ? "Datos actualizados - IA habilitada"
            : "Datos desactualizados - IA no disponible"}
        </p>
        <p style={{ margin: "0.2rem 0 0", fontSize: "0.83rem", color: "#7a5c3a" }}>
          {validez.mensaje}
        </p>
      </div>
      <div style={{ marginLeft: "auto", textAlign: "right", fontSize: "0.78rem", color: "#9a7a5a" }}>
        <p style={{ margin: 0 }}>Amb: {
          validez.horas_desde_ambiental
            ? `hace ${validez.horas_desde_ambiental.toFixed(1)} h`
            : "Sin datos"
        }</p>
        <p style={{ margin: 0 }}>Suelo: {
          validez.horas_desde_suelo
            ? `hace ${validez.horas_desde_suelo.toFixed(1)} h`
            : "Sin datos"
        }</p>
      </div>
    </div>
  );
}

function FilaHistorial({ fecha, origen, variables }) {
  const etiquetaOrigen = {
    manual:      "Manual",
    sensor_iot:  "Sensor IoT",
    laboratorio: "Laboratorio",
    api_externa: "API ext.",
  };
  return (
    <div style={{
      border: `1px solid ${COLOR.borde}`,
      borderRadius: "8px",
      padding: "0.75rem 1rem",
      background: "#fafaf8",
      display: "flex",
      justifyContent: "space-between",
      alignItems: "center",
      gap: "1rem",
    }}>
      <div style={{ fontSize: "0.8rem", color: "#9a7a5a" }}>
        <p style={{ margin: 0, fontWeight: 600 }}>
          {new Date(fecha).toLocaleDateString("es-CO", {
            day: "2-digit", month: "short", year: "numeric",
            hour: "2-digit", minute: "2-digit",
          })}
        </p>
        <span style={{
          background: "#e8ddd4", color: COLOR.cafe,
          borderRadius: "4px", padding: "1px 6px", fontSize: "0.73rem",
        }}>
          {etiquetaOrigen[origen] || origen}
        </span>
      </div>
      <div style={{ display: "flex", gap: "1.5rem", flexWrap: "wrap" }}>
        {variables.map(({ etiqueta, valor, unidad }) =>
          valor !== null && valor !== undefined ? (
            <div key={etiqueta} style={{ textAlign: "center" }}>
              <p style={{ margin: 0, fontSize: "0.73rem", color: "#9a7a5a" }}>{etiqueta}</p>
              <p style={{ margin: 0, fontSize: "0.92rem", fontWeight: 700, color: COLOR.cafe }}>
                {valor} <span style={{ fontWeight: 400, fontSize: "0.78rem" }}>{unidad}</span>
              </p>
            </div>
          ) : null
        )}
      </div>
    </div>
  );
}

// ==============================================================
// DETERMINACION DE ESTADO DE ALERTA DE UNA METRICA
// ==============================================================
function estadoTemp(v) {
  if (v === null || v === undefined) return "normal";
  if (v < 14 || v > 30) return "critico";
  if (v < 18 || v > 24) return "alerta";
  return "optimo";
}
function estadoHumRel(v) {
  if (v === null || v === undefined) return "normal";
  if (v < 55 || v > 95) return "critico";
  if (v < 70 || v > 90) return "alerta";
  return "optimo";
}
function estadoPH(v) {
  if (v === null || v === undefined) return "normal";
  if (v < 4.5 || v > 7.5) return "critico";
  if (v < 5.5 || v > 6.5) return "alerta";
  return "optimo";
}

// ==============================================================
// COMPONENTE PRINCIPAL
// ==============================================================

export default function Monitoreo() {
  // F-C01 + N-002 FIX: leer de sessionStorage (escrito por Cultivos.jsx al seleccionar)
  const cultivoId     = parseInt(sessionStorage.getItem("gv_cultivo_id") || "1", 10);
  const cultivoNombre = sessionStorage.getItem("gv_cultivo_nombre") || "Mi Cultivo";

  const { resumen, validez, cargando, error, recargar } = useMonitoreo(cultivoId, 60);
  const { historial: histAmb, recargar: recargarAmb }   = useHistorialAmbiental(cultivoId, 15);
  const { historial: histSue, recargar: recargarSue }   = useHistorialSuelo(cultivoId, 15);

  const [modalAmb,    setModalAmb]    = useState(false);
  const [modalSuelo,  setModalSuelo]  = useState(false);
  const [tabActiva,   setTabActiva]   = useState("ambiental");

  const alGuardarAmb = () => {
    setModalAmb(false);
    recargar();
    recargarAmb();
  };
  const alGuardarSuelo = () => {
    setModalSuelo(false);
    recargar();
    recargarSue();
  };

  // ==============================================================
  // RENDER
  // ==============================================================

  if (cargando && !resumen) {
    return (
      <div style={estilos.contenedor}>
        <p style={{ textAlign: "center", color: COLOR.cafeCla, padding: "3rem" }}>
          Cargando datos de monitoreo...
        </p>
      </div>
    );
  }

  return (
    <div style={estilos.contenedor}>

      {/* Encabezado */}
      <div style={estilos.encabezado}>
        <div>
          <h1 style={estilos.titulo}>🌡️ Monitoreo</h1>
          <p style={{ margin: 0, color: "#7a5c3a" }}>{cultivoNombre}</p>
        </div>
        <div style={{ display: "flex", gap: "0.8rem" }}>
          <button onClick={() => setModalAmb(true)} style={estilos.botonVerde}>
            + Ambiental
          </button>
          <button onClick={() => setModalSuelo(true)} style={estilos.botonCafe}>
            + Suelo
          </button>
        </div>
      </div>

      {/* Error global */}
      {error && (
        <div style={estilos.alerta} role="alert">{error}</div>
      )}

      {/* Banner de validez RN-03 */}
      <BannerValidez validez={validez} />

      {/* Alertas activas */}
      {resumen?.alertas?.length > 0 && (
        <div style={{
          background: "#fffbeb", border: `1px solid ${COLOR.amarillo}`,
          borderRadius: "12px", padding: "1rem 1.4rem",
        }}>
          <p style={{ margin: "0 0 0.5rem", fontWeight: 700, color: COLOR.amarillo }}>
            Alertas activas ({resumen.alertas.length})
          </p>
          {resumen.alertas.map((a, i) => (
            <p key={i} style={{ margin: "0.25rem 0", fontSize: "0.85rem", color: "#7a5c3a" }}>
              - {a}
            </p>
          ))}
        </div>
      )}

      {/* Metricas ambientales */}
      <section>
        <h2 style={estilos.seccion}>Variables Ambientales</h2>
        <div style={estilos.gridMetricas}>
          <TarjetaMetrica
            icono="🌡️" etiqueta="Temperatura"
            valor={resumen?.ultima_temperatura}
            unidad="C"
            estado={estadoTemp(resumen?.ultima_temperatura)}
          />
          <TarjetaMetrica
            icono="💧" etiqueta="Humedad relativa"
            valor={resumen?.ultima_humedad_rel}
            unidad="%"
            estado={estadoHumRel(resumen?.ultima_humedad_rel)}
          />
          <TarjetaMetrica
            icono="🌧️" etiqueta="Precipitacion"
            valor={resumen?.ultima_precipitacion}
            unidad="mm"
          />
        </div>
      </section>

      {/* Metricas de suelo */}
      <section>
        <h2 style={estilos.seccion}>Estado del Suelo</h2>
        <div style={estilos.gridMetricas}>
          <TarjetaMetrica
            icono="🧪" etiqueta="pH del suelo"
            valor={resumen?.ultimo_ph}
            estado={estadoPH(resumen?.ultimo_ph)}
          />
          <TarjetaMetrica
            icono="💦" etiqueta="Humedad suelo"
            valor={resumen?.ultima_humedad_suelo}
            unidad="%"
          />
          <TarjetaMetrica
            icono="🌿" etiqueta="Nitrogeno"
            valor={resumen?.ultimo_nitrogeno}
            unidad="mg/kg"
            estado={
              resumen?.ultimo_nitrogeno !== null && resumen?.ultimo_nitrogeno < 20
                ? "alerta" : "normal"
            }
          />
        </div>
      </section>

      {/* Historial con tabs */}
      <section>
        <div style={{ display: "flex", gap: 0, borderBottom: `2px solid ${COLOR.borde}`, marginBottom: "1rem" }}>
          {["ambiental", "suelo"].map(tab => (
            <button
              key={tab}
              onClick={() => setTabActiva(tab)}
              style={{
                padding:    "0.6rem 1.5rem",
                border:     "none",
                background: "none",
                fontWeight: tabActiva === tab ? 800 : 400,
                color:      tabActiva === tab ? COLOR.cafe : "#9a7a5a",
                borderBottom: tabActiva === tab ? `3px solid ${COLOR.cafe}` : "3px solid transparent",
                cursor:     "pointer",
                fontSize:   "0.92rem",
                marginBottom: "-2px",
              }}
            >
              {tab === "ambiental" ? "Historial Ambiental" : "Historial Suelo"}
            </button>
          ))}
        </div>

        {tabActiva === "ambiental" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
            {histAmb.length === 0 ? (
              <p style={{ color: "#bbb", fontSize: "0.9rem" }}>
                Sin lecturas ambientales registradas.
              </p>
            ) : (
              histAmb.map(r => (
                <FilaHistorial
                  key={r.id_monitoreo}
                  fecha={r.fecha_registro}
                  origen={r.origen_dato}
                  variables={[
                    { etiqueta: "Temp",    valor: r.temperatura,       unidad: "C"    },
                    { etiqueta: "Hum",     valor: r.humedad_relativa,  unidad: "%"    },
                    { etiqueta: "Lluvia",  valor: r.precipitacion_mm,  unidad: "mm"   },
                    { etiqueta: "Rad",     valor: r.radiacion_solar,   unidad: "W/m2" },
                    { etiqueta: "Viento",  valor: r.velocidad_viento,  unidad: "km/h" },
                  ]}
                />
              ))
            )}
          </div>
        )}

        {tabActiva === "suelo" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
            {histSue.length === 0 ? (
              <p style={{ color: "#bbb", fontSize: "0.9rem" }}>
                Sin lecturas de suelo registradas.
              </p>
            ) : (
              histSue.map(r => (
                <FilaHistorial
                  key={r.id_monitoreo_suelo}
                  fecha={r.fecha_registro}
                  origen={r.origen_dato}
                  variables={[
                    { etiqueta: "pH",   valor: r.ph,               unidad: ""       },
                    { etiqueta: "Hum",  valor: r.humedad_suelo,    unidad: "%"      },
                    { etiqueta: "N",    valor: r.nitrogeno,        unidad: "mg/kg"  },
                    { etiqueta: "P",    valor: r.fosforo,          unidad: "mg/kg"  },
                    { etiqueta: "K",    valor: r.potasio,          unidad: "mg/kg"  },
                    { etiqueta: "M.O.", valor: r.materia_organica, unidad: "%"      },
                  ]}
                />
              ))
            )}
          </div>
        )}
      </section>

      {/* Modal - Ambiental */}
      <Modal abierto={modalAmb} titulo="Registrar lectura ambiental" onCerrar={() => setModalAmb(false)}>
        <FormularioAmbiental
          cultivoId={cultivoId}
          onGuardado={alGuardarAmb}
          onCancelar={() => setModalAmb(false)}
        />
      </Modal>

      {/* Modal - Suelo */}
      <Modal abierto={modalSuelo} titulo="Registrar analisis de suelo" onCerrar={() => setModalSuelo(false)}>
        <FormularioSuelo
          cultivoId={cultivoId}
          onGuardado={alGuardarSuelo}
          onCancelar={() => setModalSuelo(false)}
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
    display:    "flex",
    flexDirection: "column",
    gap:        "1.5rem",
  },
  encabezado: {
    display:        "flex",
    justifyContent: "space-between",
    alignItems:     "center",
  },
  titulo: {
    margin: 0, fontSize: "1.8rem",
    fontWeight: 800, color: COLOR.cafe,
  },
  seccion: {
    margin: "0 0 0.8rem",
    fontSize: "1rem",
    fontWeight: 700,
    color: COLOR.cafe,
    borderBottom: `2px solid ${COLOR.borde}`,
    paddingBottom: "0.4rem",
  },
  gridMetricas: {
    display:             "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
    gap:                 "1rem",
  },
  alerta: {
    background: "#fff1f0", border: "1px solid #ffccc7",
    borderRadius: "8px", padding: "0.8rem 1rem",
    color: COLOR.rojo, fontSize: "0.87rem",
  },
  botonVerde: {
    padding: "0.6rem 1.2rem", borderRadius: "8px",
    border: "none", background: "#dcfce7",
    color: COLOR.verde, fontWeight: 700, cursor: "pointer",
  },
  botonCafe: {
    padding: "0.6rem 1.2rem", borderRadius: "8px",
    border: "none",
    background: "linear-gradient(135deg, #6f3a1b, #a0522d)",
    color: "#fff", fontWeight: 700, cursor: "pointer",
  },
};
