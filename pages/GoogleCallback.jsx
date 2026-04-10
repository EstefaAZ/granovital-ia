// =============================================================
// frontend/src/pages/GoogleCallback.jsx
// Página de callback para Google OAuth
// =============================================================

import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../components/AuthContext";
import { authService } from "../services/authService";

const VERDE_CAFE = "#2D6A4F";
const ROJO_ERROR = "#C73E1D";

export default function GoogleCallback() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login } = useAuth();

  const [estado, setEstado] = useState("procesando"); // procesando, exito, error
  const [mensaje, setMensaje] = useState("Verificando tu cuenta con Google...");

  useEffect(() => {
    const procesarCallback = async () => {
      try {
        // Obtener parámetros de la URL
        const code = searchParams.get("code");
        const state = searchParams.get("state");
        const error = searchParams.get("error");

        // Verificar si hay error en la URL
        if (error) {
          console.error("Error en OAuth callback:", error);
          setEstado("error");
          setMensaje("Error al autorizar con Google. Inténtalo de nuevo.");
          return;
        }

        // Verificar que tenemos el código
        if (!code) {
          setEstado("error");
          setMensaje("Código de autorización faltante.");
          return;
        }

        // Verificar state para prevenir CSRF
        const storedState = sessionStorage.getItem("google_oauth_state");
        if (state && storedState && state !== storedState) {
          setEstado("error");
          setMensaje("Error de seguridad. Inténtalo de nuevo.");
          return;
        }

        // Limpiar state almacenado
        sessionStorage.removeItem("google_oauth_state");

        // Procesar el callback con el backend
        setMensaje("Conectando con GranoVital IA...");
        const data = await authService.handleGoogleCallback(code, state);

        // Login exitoso - actualizar contexto
        await login(data.usuario, data.access_token);

        setEstado("exito");
        setMensaje("¡Bienvenido! Redirigiendo...");

        // Redirigir después de un breve delay
        setTimeout(() => {
          const ruta = determinarRutaPorRol(data.usuario.rol?.nombre_rol);
          navigate(ruta, { replace: true });
        }, 1500);

      } catch (error) {
        console.error("Error procesando callback de Google:", error);
        setEstado("error");

        if (error.status === 400) {
          setMensaje("Error en la autenticación con Google. Inténtalo de nuevo.");
        } else if (error.status === 500) {
          setMensaje("Error del servidor. Inténtalo más tarde.");
        } else {
          setMensaje("Error inesperado. Inténtalo de nuevo.");
        }
      }
    };

    procesarCallback();
  }, [searchParams, login, navigate]);

  const determinarRutaPorRol = (rolNombre) => {
    const rutas = {
      Administrador: "/admin/dashboard",
      Caficultor: "/cultivo/dashboard",
      Productor: "/produccion/dashboard",
      Comercializador: "/mercado/dashboard",
      Consumidor: "/trazabilidad/consulta",
    };
    return rutas[rolNombre] || "/dashboard";
  };

  const handleReintentar = () => {
    navigate("/login", { replace: true });
  };

  return (
    <div style={styles.pagina}>
      <div style={styles.contenedor}>
        <div style={styles.tarjeta}>
          <div style={styles.encabezado}>
            <div style={styles.logoIcono}>☕</div>
            <h1 style={styles.titulo}>GranoVital IA</h1>
          </div>

          <div style={styles.contenido}>
            {estado === "procesando" && (
              <div style={styles.estadoProcesando}>
                <div style={styles.spinner}></div>
                <p style={styles.mensaje}>{mensaje}</p>
              </div>
            )}

            {estado === "exito" && (
              <div style={styles.estadoExito}>
                <span style={styles.iconoExito}>✅</span>
                <p style={styles.mensaje}>{mensaje}</p>
              </div>
            )}

            {estado === "error" && (
              <div style={styles.estadoError}>
                <span style={styles.iconoError}>❌</span>
                <p style={styles.mensaje}>{mensaje}</p>
                <button
                  onClick={handleReintentar}
                  style={styles.botonReintentar}
                >
                  Volver al inicio de sesión
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

const styles = {
  pagina: {
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#F0F4F0",
    fontFamily: "'Segoe UI', Arial, sans-serif",
  },
  contenedor: {
    width: "100%",
    maxWidth: "400px",
    padding: "20px",
  },
  tarjeta: {
    backgroundColor: "white",
    borderRadius: "16px",
    padding: "40px 32px",
    boxShadow: "0 4px 24px rgba(0,0,0,0.10)",
    textAlign: "center",
  },
  encabezado: {
    marginBottom: "32px",
  },
  logoIcono: {
    fontSize: "48px",
    marginBottom: "8px",
  },
  titulo: {
    fontSize: "24px",
    fontWeight: "800",
    color: VERDE_CAFE,
    margin: "0",
  },
  contenido: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
  },
  estadoProcesando: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "16px",
  },
  estadoExito: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "16px",
  },
  estadoError: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "16px",
  },
  spinner: {
    width: "40px",
    height: "40px",
    border: "4px solid #f3f3f3",
    borderTop: `4px solid ${VERDE_CAFE}`,
    borderRadius: "50%",
    animation: "spin 1s linear infinite",
  },
  iconoExito: {
    fontSize: "48px",
  },
  iconoError: {
    fontSize: "48px",
    color: ROJO_ERROR,
  },
  mensaje: {
    fontSize: "16px",
    color: "#333",
    margin: "0",
    lineHeight: "1.5",
  },
  botonReintentar: {
    backgroundColor: VERDE_CAFE,
    color: "white",
    border: "none",
    borderRadius: "8px",
    padding: "12px 24px",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
    transition: "all 0.2s",
    marginTop: "8px",
  },
};

// CSS para el spinner
const styleSheet = document.createElement("style");
styleSheet.textContent = `
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
`;
document.head.appendChild(styleSheet);