// =============================================================
// frontend/src/pages/Login.jsx
// Página de inicio de sesión — GranoVital IA
// Trazabilidad: RF-01 | RNF-02 (usabilidad) | RNF-07 (web/móvil)
// =============================================================

import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../components/AuthContext";
import { ApiError } from "../services/authService";

// ── Mapa de rutas por rol (RN-01 — acceso según rol) ──────────
const RUTAS_POR_ROL = {
  Administrador:    "/admin/dashboard",
  Caficultor:       "/cultivo/dashboard",
  Productor:        "/produccion/dashboard",
  Comercializador:  "/mercado/dashboard",
  Consumidor:       "/trazabilidad/consulta",
};

export default function Login() {
  const navigate    = useNavigate();
  const { login, estaAutenticado, usuario } = useAuth();

  // ── Estado del formulario ───────────────────────────────────
  const [correo,      setCorreo]      = useState("");
  const [contrasena,  setContrasena]  = useState("");
  const [mostrarPass, setMostrarPass] = useState(false);
  const [cargando,    setCargando]    = useState(false);
  const [errores,     setErrores]     = useState({});
  const [errorApi,    setErrorApi]    = useState("");

  // Si ya está autenticado, redirigir a su ruta por rol
  useEffect(() => {
    if (estaAutenticado && usuario) {
      const ruta = RUTAS_POR_ROL[usuario.rol?.nombre_rol] || "/dashboard";
      navigate(ruta, { replace: true });
    }
  }, [estaAutenticado, usuario, navigate]);

  // ── Validación del formulario ───────────────────────────────
  const validar = () => {
    const nuevosErrores = {};
    const regexEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!correo.trim()) {
      nuevosErrores.correo = "El correo electrónico es obligatorio";
    } else if (!regexEmail.test(correo)) {
      nuevosErrores.correo = "Ingresa un correo electrónico válido";
    }

    if (!contrasena) {
      nuevosErrores.contrasena = "La contraseña es obligatoria";
    } else if (contrasena.length < 6) {
      nuevosErrores.contrasena = "La contraseña debe tener al menos 6 caracteres";
    }

    setErrores(nuevosErrores);
    return Object.keys(nuevosErrores).length === 0;
  };

  // ── Envío del formulario ────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorApi("");

    if (!validar()) return;

    setCargando(true);
    try {
      const data = await login(correo.trim().toLowerCase(), contrasena);
      const rol   = data.usuario?.rol?.nombre_rol;
      const ruta  = RUTAS_POR_ROL[rol] || "/dashboard";
      navigate(ruta, { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        switch (err.status) {
          case 401:
            setErrorApi("Correo electrónico o contraseña incorrectos. Verifica tus datos.");
            break;
          case 403:
            setErrorApi("Tu cuenta está suspendida o inactiva. Contacta al administrador.");
            break;
          case 429:
            setErrorApi(
              "Tu cuenta ha sido bloqueada temporalmente por múltiples intentos fallidos. " +
              "Contacta al administrador del sistema."
            );
            break;
          case 422:
            setErrorApi("Por favor verifica el formato del correo y la contraseña.");
            break;
          default:
            setErrorApi("Error del servidor. Por favor intenta nuevamente en unos minutos.");
        }
      } else {
        setErrorApi("No se pudo conectar al servidor. Verifica tu conexión a internet.");
      }
    } finally {
      setCargando(false);
    }
  };

  // ── Limpiar error de campo al escribir ──────────────────────
  const handleCorreoChange = (e) => {
    setCorreo(e.target.value);
    if (errores.correo) setErrores((prev) => ({ ...prev, correo: "" }));
    setErrorApi("");
  };

  const handlePassChange = (e) => {
    setContrasena(e.target.value);
    if (errores.contrasena) setErrores((prev) => ({ ...prev, contrasena: "" }));
    setErrorApi("");
  };

  // ── Render ──────────────────────────────────────────────────
  return (
    <div style={styles.pagina}>
      {/* Fondo decorativo */}
      <div style={styles.fondo} aria-hidden="true" />

      <div style={styles.contenedor}>
        {/* Encabezado */}
        <div style={styles.encabezado}>
          <div style={styles.logoIcono} aria-label="Logo GranoVital IA">
            ☕
          </div>
          <h1 style={styles.titulo}>GranoVital IA</h1>
          <p style={styles.subtitulo}>
            Gestión inteligente del café
          </p>
        </div>

        {/* Tarjeta del formulario */}
        <div style={styles.tarjeta}>
          <h2 style={styles.tituloFormulario}>Iniciar sesión</h2>
          <p style={styles.descripcion}>
            Accede con las credenciales asignadas según tu rol en el sistema.
          </p>

          {/* Alerta de error de API */}
          {errorApi && (
            <div style={styles.alertaError} role="alert" aria-live="polite">
              <span style={styles.iconoAlerta}>⚠</span>
              <span>{errorApi}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate style={styles.formulario}>
            {/* Campo correo */}
            <div style={styles.grupo}>
              <label htmlFor="correo" style={styles.etiqueta}>
                Correo electrónico
              </label>
              <input
                id="correo"
                type="email"
                value={correo}
                onChange={handleCorreoChange}
                placeholder="usuario@granovital.co"
                autoComplete="email"
                autoFocus
                disabled={cargando}
                aria-describedby={errores.correo ? "error-correo" : undefined}
                aria-invalid={!!errores.correo}
                style={{
                  ...styles.input,
                  ...(errores.correo ? styles.inputError : {}),
                }}
              />
              {errores.correo && (
                <span id="error-correo" style={styles.mensajeError} role="alert">
                  {errores.correo}
                </span>
              )}
            </div>

            {/* Campo contraseña */}
            <div style={styles.grupo}>
              <label htmlFor="contrasena" style={styles.etiqueta}>
                Contraseña
              </label>
              <div style={styles.contenedorPassword}>
                <input
                  id="contrasena"
                  type={mostrarPass ? "text" : "password"}
                  value={contrasena}
                  onChange={handlePassChange}
                  placeholder="Tu contraseña"
                  autoComplete="current-password"
                  disabled={cargando}
                  aria-describedby={errores.contrasena ? "error-contrasena" : undefined}
                  aria-invalid={!!errores.contrasena}
                  style={{
                    ...styles.input,
                    paddingRight: "48px",
                    ...(errores.contrasena ? styles.inputError : {}),
                  }}
                />
                <button
                  type="button"
                  onClick={() => setMostrarPass(!mostrarPass)}
                  style={styles.botonVerPass}
                  aria-label={mostrarPass ? "Ocultar contraseña" : "Mostrar contraseña"}
                  tabIndex={-1}
                >
                  {mostrarPass ? "🙈" : "👁"}
                </button>
              </div>
              {errores.contrasena && (
                <span id="error-contrasena" style={styles.mensajeError} role="alert">
                  {errores.contrasena}
                </span>
              )}
            </div>

            {/* Botón de login */}
            <button
              type="submit"
              disabled={cargando}
              style={{
                ...styles.botonPrincipal,
                ...(cargando ? styles.botonDeshabilitado : {}),
              }}
              aria-busy={cargando}
            >
              {cargando ? (
                <span style={styles.contenedorCargando}>
                  <span style={styles.spinner} aria-hidden="true" />
                  Verificando credenciales...
                </span>
              ) : (
                "Ingresar al sistema"
              )}
            </button>
          </form>

          {/* Información de roles */}
          <div style={styles.infoRoles}>
            <p style={styles.infoRolesTexto}>
              Roles disponibles en el sistema:
            </p>
            <div style={styles.chips}>
              {["Administrador", "Caficultor", "Productor", "Comercializador", "Consumidor"].map(
                (rol) => (
                  <span key={rol} style={styles.chip}>
                    {rol}
                  </span>
                )
              )}
            </div>
          </div>
        </div>

        {/* Pie de página */}
        <p style={styles.footer}>
          Universidad Católica Luis Amigó · GranoVital IA v1.0
        </p>
      </div>
    </div>
  );
}

// =============================================================
// ESTILOS (CSS-in-JS — compatible con React Native básico)
// =============================================================
const VERDE_CAFE  = "#2D6A4F";
const VERDE_CLARO = "#40916C";
const CAFE        = "#6B4226";
const GRIS_FONDO  = "#F0F4F0";
const ROJO_ERROR  = "#C73E1D";

const styles = {
  pagina: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: GRIS_FONDO,
    fontFamily: "'Segoe UI', Arial, sans-serif",
    padding: "20px",
    position: "relative",
    overflow: "hidden",
  },
  fondo: {
    position: "absolute",
    top: 0, left: 0, right: 0, bottom: 0,
    background: `linear-gradient(135deg, ${VERDE_CAFE}22 0%, ${CAFE}11 100%)`,
    backgroundImage: "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%232D6A4F' fill-opacity='0.04'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")",
    pointerEvents: "none",
  },
  contenedor: {
    width: "100%",
    maxWidth: "440px",
    position: "relative",
    zIndex: 1,
  },
  encabezado: {
    textAlign: "center",
    marginBottom: "24px",
  },
  logoIcono: {
    fontSize: "52px",
    display: "block",
    marginBottom: "8px",
    filter: "drop-shadow(0 4px 8px rgba(0,0,0,0.15))",
  },
  titulo: {
    fontSize: "28px",
    fontWeight: "800",
    color: VERDE_CAFE,
    margin: "0 0 4px 0",
    letterSpacing: "-0.5px",
  },
  subtitulo: {
    fontSize: "14px",
    color: "#666",
    margin: 0,
  },
  tarjeta: {
    backgroundColor: "white",
    borderRadius: "16px",
    padding: "36px 40px",
    boxShadow: "0 4px 24px rgba(0,0,0,0.10), 0 1px 4px rgba(0,0,0,0.06)",
  },
  tituloFormulario: {
    fontSize: "20px",
    fontWeight: "700",
    color: "#1A1A1A",
    margin: "0 0 6px 0",
  },
  descripcion: {
    fontSize: "13px",
    color: "#777",
    margin: "0 0 24px 0",
    lineHeight: "1.5",
  },
  alertaError: {
    backgroundColor: "#FEF2F2",
    border: `1px solid ${ROJO_ERROR}44`,
    borderLeft: `4px solid ${ROJO_ERROR}`,
    borderRadius: "8px",
    padding: "12px 16px",
    marginBottom: "20px",
    display: "flex",
    alignItems: "flex-start",
    gap: "10px",
    fontSize: "13px",
    color: ROJO_ERROR,
    lineHeight: "1.5",
  },
  iconoAlerta: {
    fontSize: "16px",
    flexShrink: 0,
    marginTop: "1px",
  },
  formulario: {
    display: "flex",
    flexDirection: "column",
    gap: "20px",
  },
  grupo: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  etiqueta: {
    fontSize: "13px",
    fontWeight: "600",
    color: "#333",
  },
  input: {
    width: "100%",
    padding: "11px 14px",
    fontSize: "15px",
    border: "1.5px solid #DDD",
    borderRadius: "8px",
    outline: "none",
    transition: "border-color 0.2s, box-shadow 0.2s",
    boxSizing: "border-box",
    backgroundColor: "#FAFAFA",
    color: "#1A1A1A",
  },
  inputError: {
    borderColor: ROJO_ERROR,
    backgroundColor: "#FFF8F8",
  },
  mensajeError: {
    fontSize: "12px",
    color: ROJO_ERROR,
    fontWeight: "500",
  },
  contenedorPassword: {
    position: "relative",
  },
  botonVerPass: {
    position: "absolute",
    right: "12px",
    top: "50%",
    transform: "translateY(-50%)",
    background: "none",
    border: "none",
    cursor: "pointer",
    fontSize: "16px",
    padding: "4px",
    lineHeight: 1,
  },
  botonPrincipal: {
    width: "100%",
    padding: "13px",
    backgroundColor: VERDE_CAFE,
    color: "white",
    border: "none",
    borderRadius: "8px",
    fontSize: "15px",
    fontWeight: "700",
    cursor: "pointer",
    transition: "background-color 0.2s, transform 0.1s",
    marginTop: "4px",
  },
  botonDeshabilitado: {
    backgroundColor: "#9CA3AF",
    cursor: "not-allowed",
    transform: "none",
  },
  contenedorCargando: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "10px",
  },
  spinner: {
    display: "inline-block",
    width: "16px",
    height: "16px",
    border: "2px solid rgba(255,255,255,0.3)",
    borderTopColor: "white",
    borderRadius: "50%",
    animation: "spin 0.8s linear infinite",
  },
  infoRoles: {
    marginTop: "28px",
    paddingTop: "20px",
    borderTop: "1px solid #F0F0F0",
  },
  infoRolesTexto: {
    fontSize: "11px",
    color: "#AAA",
    margin: "0 0 8px 0",
    textTransform: "uppercase",
    letterSpacing: "0.5px",
    fontWeight: "600",
  },
  chips: {
    display: "flex",
    flexWrap: "wrap",
    gap: "6px",
  },
  chip: {
    fontSize: "11px",
    backgroundColor: `${VERDE_CAFE}15`,
    color: VERDE_CAFE,
    padding: "3px 10px",
    borderRadius: "20px",
    fontWeight: "600",
    border: `1px solid ${VERDE_CAFE}30`,
  },
  footer: {
    textAlign: "center",
    fontSize: "11px",
    color: "#AAA",
    marginTop: "20px",
  },
};
