// =============================================================
// frontend/src/pages/Login.jsx
// Página de inicio de sesión — GranoVital IA
//
// SEC-004 FIX: bloqueo de UI tras múltiples intentos fallidos
// UX-003  FIX: @keyframes 'spin' agregado para que el spinner gire
// AUTH-001 NOTA: Las rutas legacy en App.jsx ahora verifican el rol
// =============================================================

import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../components/AuthContext";
import { ApiError, authService } from "../services/authService";

const RUTAS_POR_ROL = {
  Administrador:   "/admin/dashboard",
  Caficultor:      "/cultivo/dashboard",
  Productor:       "/produccion/dashboard",
  Comercializador: "/mercado/dashboard",
  Consumidor:      "/trazabilidad/consulta",
};

// SEC-004: máximo de intentos antes del bloqueo
const INTENTOS_MAX  = 5;
const BLOQUEO_SEG   = 30;

export default function Login() {
  const navigate = useNavigate();
  const { login, estaAutenticado, usuario } = useAuth();

  const [correo,      setCorreo]      = useState("");
  const [contrasena,  setContrasena]  = useState("");
  const [mostrarPass, setMostrarPass] = useState(false);
  const [cargando,    setCargando]    = useState(false);
  const [errores,     setErrores]     = useState({});
  const [errorApi,    setErrorApi]    = useState("");

  // SEC-004: estado de bloqueo por fuerza bruta
  const [bloqueado,       setBloqueado]       = useState(false);
  const [segsRestantes,   setSegsRestantes]   = useState(0);
  const [intentosFallidos, setIntentosFallidos] = useState(0);
  const temporizadorRef = useRef(null);

  useEffect(() => {
    if (estaAutenticado && usuario) {
      const ruta = RUTAS_POR_ROL[usuario.rol?.nombre_rol] || "/dashboard";
      navigate(ruta, { replace: true });
    }
  }, [estaAutenticado, usuario, navigate]);

  // SEC-004: sincronizar estado de bloqueo con authService al montar
  useEffect(() => {
    const estado = authService.estasBloqueado();
    if (estado.bloqueado) {
      iniciarCuentaRegresiva(Math.ceil(estado.msRestantes / 1000));
    }
    setIntentosFallidos(authService.getIntentosFallidos());
  }, []);

  // Limpieza del temporizador al desmontar
  useEffect(() => {
    return () => { if (temporizadorRef.current) clearInterval(temporizadorRef.current); };
  }, []);

  // SEC-004: iniciar cuenta regresiva visual de bloqueo
  const iniciarCuentaRegresiva = (segundos) => {
    setBloqueado(true);
    setSegsRestantes(segundos);
    if (temporizadorRef.current) clearInterval(temporizadorRef.current);
    temporizadorRef.current = setInterval(() => {
      setSegsRestantes(prev => {
        if (prev <= 1) {
          clearInterval(temporizadorRef.current);
          setBloqueado(false);
          setErrorApi("");
          setIntentosFallidos(0);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorApi("");

    // SEC-004: verificar bloqueo antes de procesar
    if (bloqueado) {
      setErrorApi(`Espera ${segsRestantes} segundos antes de intentar nuevamente.`);
      return;
    }

    if (!validar()) return;

    setCargando(true);
    try {
      const data = await login(correo.trim().toLowerCase(), contrasena);
      // Login exitoso: resetear contadores
      setIntentosFallidos(0);
      setBloqueado(false);
      const rol  = data.usuario?.rol?.nombre_rol;
      const ruta = RUTAS_POR_ROL[rol] || "/dashboard";
      navigate(ruta, { replace: true });
    } catch (err) {
      // SEC-004: actualizar contador de intentos desde authService
      const nuevosIntentos = authService.getIntentosFallidos();
      setIntentosFallidos(nuevosIntentos);

      // Verificar si el bloqueo fue activado por este intento
      const estadoBloqueo = authService.estasBloqueado();
      if (estadoBloqueo.bloqueado) {
        iniciarCuentaRegresiva(BLOQUEO_SEG);
        setErrorApi(
          `Has superado ${INTENTOS_MAX} intentos fallidos. El formulario estará bloqueado por ${BLOQUEO_SEG} segundos.`
        );
      } else if (err instanceof ApiError) {
        switch (err.status) {
          case 401:
            setErrorApi(
              nuevosIntentos > 0
                ? `Correo o contraseña incorrectos. Intento ${nuevosIntentos} de ${INTENTOS_MAX}.`
                : "Correo electrónico o contraseña incorrectos."
            );
            break;
          case 403:
            setErrorApi("Tu cuenta está suspendida o inactiva. Contacta al administrador.");
            break;
          case 429:
            iniciarCuentaRegresiva(BLOQUEO_SEG);
            setErrorApi(
              `Demasiados intentos fallidos. Tu acceso está bloqueado temporalmente por ${BLOQUEO_SEG} segundos.`
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

  const formularioDeshabilitado = cargando || bloqueado;

  return (
    <div style={styles.pagina}>
      {/* UX-003 FIX: @keyframes spin declarado inline para que el spinner gire */}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @keyframes pulso {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>

      <div style={styles.fondo} aria-hidden="true" />

      <div style={styles.contenedor}>
        <div style={styles.encabezado}>
          <div style={styles.logoIcono} aria-label="Logo GranoVital IA">☕</div>
          <h1 style={styles.titulo}>GranoVital IA</h1>
          <p style={styles.subtitulo}>Gestión inteligente del café</p>
        </div>

        <div style={styles.tarjeta}>
          <h2 style={styles.tituloFormulario}>Iniciar sesión</h2>
          <p style={styles.descripcion}>
            Accede con las credenciales asignadas según tu rol en el sistema.
          </p>

          {/* SEC-004: barra de progreso de intentos */}
          {intentosFallidos > 0 && !bloqueado && (
            <div style={styles.barraIntentos} role="status" aria-live="polite">
              <div style={{
                ...styles.barraIntentosRelleno,
                width: `${(intentosFallidos / INTENTOS_MAX) * 100}%`,
                background: intentosFallidos >= 4 ? "#C73E1D" : "#c8a000",
              }} />
              <span style={styles.textoIntentos}>
                {intentosFallidos} de {INTENTOS_MAX} intentos fallidos
              </span>
            </div>
          )}

          {/* SEC-004: banner de bloqueo activo */}
          {bloqueado && (
            <div style={styles.alertaBloqueo} role="alert" aria-live="assertive">
              <span style={{ fontSize: "1.2rem" }}>🔒</span>
              <div>
                <strong>Formulario bloqueado</strong>
                <p style={{ margin: "0.2rem 0 0", fontSize: "0.85rem" }}>
                  Tiempo restante: <strong>{segsRestantes}</strong> segundos
                </p>
              </div>
            </div>
          )}

          {errorApi && !bloqueado && (
            <div style={styles.alertaError} role="alert" aria-live="polite">
              <span style={styles.iconoAlerta}>⚠</span>
              <span>{errorApi}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} noValidate style={styles.formulario}>
            <div style={styles.grupo}>
              <label htmlFor="correo" style={styles.etiqueta}>Correo electrónico</label>
              <input
                id="correo"
                type="email"
                value={correo}
                onChange={handleCorreoChange}
                placeholder="usuario@granovital.co"
                autoComplete="email"
                autoFocus
                disabled={formularioDeshabilitado}
                aria-describedby={errores.correo ? "error-correo" : undefined}
                aria-invalid={!!errores.correo}
                style={{
                  ...styles.input,
                  ...(errores.correo ? styles.inputError : {}),
                  opacity: formularioDeshabilitado ? 0.6 : 1,
                }}
              />
              {errores.correo && (
                <span id="error-correo" style={styles.mensajeError} role="alert">
                  {errores.correo}
                </span>
              )}
            </div>

            <div style={styles.grupo}>
              <label htmlFor="contrasena" style={styles.etiqueta}>Contraseña</label>
              <div style={styles.contenedorPassword}>
                <input
                  id="contrasena"
                  type={mostrarPass ? "text" : "password"}
                  value={contrasena}
                  onChange={handlePassChange}
                  placeholder="Tu contraseña"
                  autoComplete="current-password"
                  disabled={formularioDeshabilitado}
                  aria-describedby={errores.contrasena ? "error-contrasena" : undefined}
                  aria-invalid={!!errores.contrasena}
                  style={{
                    ...styles.input,
                    paddingRight: "48px",
                    ...(errores.contrasena ? styles.inputError : {}),
                    opacity: formularioDeshabilitado ? 0.6 : 1,
                  }}
                />
                <button
                  type="button"
                  onClick={() => setMostrarPass(!mostrarPass)}
                  disabled={formularioDeshabilitado}
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

            <button
              type="submit"
              disabled={formularioDeshabilitado}
              style={{
                ...styles.botonPrincipal,
                ...(formularioDeshabilitado ? styles.botonDeshabilitado : {}),
              }}
              aria-busy={cargando}
              aria-disabled={formularioDeshabilitado}
            >
              {cargando ? (
                <span style={styles.contenedorCargando}>
                  {/* UX-003 FIX: el spinner ahora gira gracias al @keyframes spin */}
                  <span
                    style={styles.spinner}
                    aria-hidden="true"
                    role="presentation"
                  />
                  Verificando credenciales...
                </span>
              ) : bloqueado ? (
                `🔒 Bloqueado — espera ${segsRestantes}s`
              ) : (
                "Ingresar al sistema"
              )}
            </button>
          </form>

          <div style={styles.infoRoles}>
            <p style={styles.infoRolesTexto}>Roles disponibles en el sistema:</p>
            <div style={styles.chips}>
              {["Administrador", "Caficultor", "Productor", "Comercializador", "Consumidor"].map(
                (rol) => (
                  <span key={rol} style={styles.chip}>{rol}</span>
                )
              )}
            </div>
          </div>
        </div>

        <p style={styles.footer}>
          Universidad Católica Luis Amigó · GranoVital IA v1.0
        </p>
      </div>
    </div>
  );
}

// =============================================================
// ESTILOS
// =============================================================
const VERDE_CAFE  = "#2D6A4F";
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
  // SEC-004: barra de progreso de intentos
  barraIntentos: {
    position: "relative",
    height: "6px",
    background: "#F0F0F0",
    borderRadius: "3px",
    marginBottom: "16px",
    overflow: "hidden",
  },
  barraIntentosRelleno: {
    height: "100%",
    borderRadius: "3px",
    transition: "width 0.3s ease, background 0.3s ease",
  },
  textoIntentos: {
    position: "absolute",
    bottom: "-18px",
    right: 0,
    fontSize: "11px",
    color: "#999",
  },
  // SEC-004: banner de bloqueo
  alertaBloqueo: {
    backgroundColor: "#FFF3CD",
    border: "1px solid #c8a000",
    borderLeft: "4px solid #c8a000",
    borderRadius: "8px",
    padding: "12px 16px",
    marginBottom: "20px",
    display: "flex",
    alignItems: "flex-start",
    gap: "12px",
    fontSize: "13px",
    color: "#92400E",
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
  // UX-003 FIX: animation referencia el keyframe 'spin' declarado en <style>
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
