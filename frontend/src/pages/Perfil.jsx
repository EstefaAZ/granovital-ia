// =============================================================
// frontend/src/pages/Perfil.jsx
// Página de perfil del usuario autenticado — GranoVital IA
// RF-02 | RNF-02 Usabilidad | RNF-04 Seguridad
// =============================================================

import { useState } from "react";
import { useAuth } from "../components/AuthContext";
import { authService } from "../services/authService";

const C = {
  cafeOscuro:  "#2C1A0E",
  cafeMedio:   "#5C3317",
  cafeClaro:   "#8B5E3C",
  cafeSuave:   "#C49A6C",
  crema:       "#F5ECD7",
  cremaOscura: "#EAD9BF",
  verdeHoja:   "#4A7C59",
  rojo:        "#B91C1C",
};

function Campo({ label, value, editable = false, type = "text", onChange }) {
  return (
    <div style={{ marginBottom: "1.2rem" }}>
      <label style={{
        display: "block", fontSize: "0.78rem", fontWeight: 500,
        color: C.cafeClaro, marginBottom: "0.3rem",
        textTransform: "uppercase", letterSpacing: "0.06em",
      }}>
        {label}
      </label>
      {editable ? (
        <input
          type={type}
          value={value}
          onChange={e => onChange(e.target.value)}
          style={{
            width: "100%", padding: "0.65rem 0.9rem",
            border: `1.5px solid ${C.cremaOscura}`,
            borderRadius: "8px", fontSize: "0.95rem",
            fontFamily: "DM Sans, sans-serif",
            background: "#fff", color: C.cafeOscuro,
            outline: "none", boxSizing: "border-box",
            transition: "border-color 0.2s",
          }}
          onFocus={e => e.target.style.borderColor = C.cafeSuave}
          onBlur={e => e.target.style.borderColor = C.cremaOscura}
        />
      ) : (
        <div style={{
          padding: "0.65rem 0.9rem",
          background: C.crema,
          border: `1px solid ${C.cremaOscura}`,
          borderRadius: "8px",
          fontSize: "0.95rem",
          color: C.cafeMedio,
        }}>
          {value || "—"}
        </div>
      )}
    </div>
  );
}

function Alerta({ tipo, mensaje, onCerrar }) {
  if (!mensaje) return null;
  const cfg = tipo === "exito"
    ? { bg: "#F0FDF4", borde: "#4A7C59", texto: "#166534" }
    : { bg: "#FEF2F2", borde: C.rojo, texto: C.rojo };
  return (
    <div style={{
      background: cfg.bg, border: `1px solid ${cfg.borde}`,
      borderRadius: "8px", padding: "0.8rem 1rem",
      color: cfg.texto, fontSize: "0.88rem",
      display: "flex", justifyContent: "space-between",
      alignItems: "center", marginBottom: "1.2rem",
    }}>
      <span>{mensaje}</span>
      <button onClick={onCerrar} style={{
        background: "none", border: "none",
        cursor: "pointer", color: cfg.texto, fontSize: "1.1rem",
      }}>✕</button>
    </div>
  );
}

export default function Perfil() {
  const { usuario, logout } = useAuth();

  // Estado cambio de contraseña
  const [contrasenaActual,    setContrasenaActual]    = useState("");
  const [contrasenaNueva,     setContrasenaNueva]     = useState("");
  const [contrasenaConfirmar, setContrasenaConfirmar] = useState("");
  const [guardandoPass,       setGuardandoPass]       = useState(false);
  const [alerta,              setAlerta]              = useState({ tipo: "", msg: "" });

  if (!usuario) {
    return (
      <div style={{ padding: "3rem", textAlign: "center", color: C.cafeSuave }}>
        Cargando perfil...
      </div>
    );
  }

  const inicial = usuario.nombre?.charAt(0).toUpperCase() || "U";
  const nombreCompleto = `${usuario.nombre || ""} ${usuario.apellido || ""}`.trim();
  const fechaAcceso = usuario.ultimo_acceso
    ? new Date(usuario.ultimo_acceso).toLocaleString("es-CO")
    : "Primera sesión";

  const cambiarPassword = async (e) => {
    e.preventDefault();
    setAlerta({ tipo: "", msg: "" });

    if (!contrasenaActual || !contrasenaNueva || !contrasenaConfirmar) {
      setAlerta({ tipo: "error", msg: "Todos los campos de contraseña son obligatorios." });
      return;
    }
    if (contrasenaNueva !== contrasenaConfirmar) {
      setAlerta({ tipo: "error", msg: "Las contraseñas nuevas no coinciden." });
      return;
    }
    if (contrasenaNueva.length < 8) {
      setAlerta({ tipo: "error", msg: "La nueva contraseña debe tener al menos 8 caracteres." });
      return;
    }
    if (!/[A-Z]/.test(contrasenaNueva) || !/[0-9]/.test(contrasenaNueva)) {
      setAlerta({ tipo: "error", msg: "La contraseña debe tener al menos una mayúscula y un número." });
      return;
    }

    setGuardandoPass(true);
    try {
      await authService.cambiarPassword(contrasenaActual, contrasenaNueva, contrasenaConfirmar);
      setAlerta({ tipo: "exito", msg: "Contraseña actualizada correctamente." });
      setContrasenaActual("");
      setContrasenaNueva("");
      setContrasenaConfirmar("");
    } catch (err) {
      setAlerta({ tipo: "error", msg: err.message || "Error al cambiar la contraseña." });
    } finally {
      setGuardandoPass(false);
    }
  };

  return (
    <div style={{
      maxWidth: "760px",
      margin: "0 auto",
      fontFamily: "DM Sans, sans-serif",
      color: C.cafeOscuro,
    }}>

      {/* Encabezado del perfil */}
      <div style={{
        background: "#fff",
        borderRadius: "16px",
        border: `1px solid ${C.cremaOscura}`,
        padding: "2rem",
        marginBottom: "1.5rem",
        display: "flex",
        alignItems: "center",
        gap: "1.5rem",
      }}>
        {/* Avatar grande */}
        <div style={{
          width: "72px", height: "72px",
          background: `linear-gradient(135deg, ${C.cafeMedio}, ${C.cafeClaro})`,
          borderRadius: "50%",
          display: "flex", alignItems: "center", justifyContent: "center",
          color: C.crema,
          fontSize: "28px",
          fontFamily: "Playfair Display, serif",
          fontWeight: 700,
          flexShrink: 0,
        }}>
          {inicial}
        </div>

        <div style={{ flex: 1 }}>
          <h1 style={{
            margin: 0, fontSize: "1.5rem",
            fontFamily: "Playfair Display, serif",
            color: C.cafeOscuro, fontWeight: 700,
          }}>
            {nombreCompleto || "Usuario"}
          </h1>
          <div style={{ display: "flex", gap: "0.8rem", marginTop: "0.4rem", flexWrap: "wrap" }}>
            <span style={{
              background: `${C.cafeSuave}22`,
              border: `1px solid ${C.cafeSuave}55`,
              color: C.cafeMedio,
              borderRadius: "20px", padding: "0.2rem 0.8rem",
              fontSize: "0.8rem", fontWeight: 500,
            }}>
              {usuario.rol?.nombre_rol || "Sin rol"}
            </span>
            <span style={{
              background: usuario.estado_cuenta === "activo" ? "#F0FDF4" : "#FEF2F2",
              border: `1px solid ${usuario.estado_cuenta === "activo" ? "#4A7C59" : C.rojo}`,
              color: usuario.estado_cuenta === "activo" ? "#166534" : C.rojo,
              borderRadius: "20px", padding: "0.2rem 0.8rem",
              fontSize: "0.8rem", fontWeight: 500,
            }}>
              {usuario.estado_cuenta === "activo" ? "Cuenta activa" : usuario.estado_cuenta}
            </span>
          </div>
          <p style={{ margin: "0.5rem 0 0", fontSize: "0.82rem", color: C.cafeClaro }}>
            Último acceso: {fechaAcceso}
          </p>
        </div>
      </div>

      {/* Información de la cuenta */}
      <div style={{
        background: "#fff",
        borderRadius: "16px",
        border: `1px solid ${C.cremaOscura}`,
        padding: "1.5rem 2rem",
        marginBottom: "1.5rem",
      }}>
        <h2 style={{
          margin: "0 0 1.2rem",
          fontSize: "1rem",
          fontWeight: 600,
          color: C.cafeMedio,
          borderBottom: `2px solid ${C.cremaOscura}`,
          paddingBottom: "0.6rem",
        }}>
          Información de la cuenta
        </h2>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 1.5rem" }}>
          <Campo label="Nombre"   value={usuario.nombre}   />
          <Campo label="Apellido" value={usuario.apellido} />
          <Campo label="Correo electrónico" value={usuario.correo} />
          <Campo label="Teléfono" value={usuario.telefono} />
          <Campo label="Rol en el sistema"  value={usuario.rol?.nombre_rol} />
          <Campo label="ID de usuario"      value={`#${usuario.id_usuario}`} />
        </div>

        <p style={{ margin: "0.5rem 0 0", fontSize: "0.8rem", color: C.cafeSuave }}>
          Para actualizar tu nombre, apellido o correo, contacta al administrador del sistema.
        </p>
      </div>

      {/* Cambio de contraseña */}
      <div style={{
        background: "#fff",
        borderRadius: "16px",
        border: `1px solid ${C.cremaOscura}`,
        padding: "1.5rem 2rem",
      }}>
        <h2 style={{
          margin: "0 0 1.2rem",
          fontSize: "1rem",
          fontWeight: 600,
          color: C.cafeMedio,
          borderBottom: `2px solid ${C.cremaOscura}`,
          paddingBottom: "0.6rem",
        }}>
          Cambiar contraseña
        </h2>

        <Alerta
          tipo={alerta.tipo}
          mensaje={alerta.msg}
          onCerrar={() => setAlerta({ tipo: "", msg: "" })}
        />

        <form onSubmit={cambiarPassword}>
          <Campo
            label="Contraseña actual"
            type="password"
            value={contrasenaActual}
            editable
            onChange={setContrasenaActual}
          />
          <Campo
            label="Nueva contraseña"
            type="password"
            value={contrasenaNueva}
            editable
            onChange={setContrasenaNueva}
          />
          <p style={{ margin: "-0.8rem 0 1rem", fontSize: "0.75rem", color: C.cafeSuave }}>
            Mínimo 8 caracteres, una mayúscula y un número.
          </p>
          <Campo
            label="Confirmar nueva contraseña"
            type="password"
            value={contrasenaConfirmar}
            editable
            onChange={setContrasenaConfirmar}
          />

          <button
            type="submit"
            disabled={guardandoPass}
            style={{
              padding: "0.7rem 1.8rem",
              borderRadius: "8px", border: "none",
              background: guardandoPass ? C.cafeSuave : C.cafeMedio,
              color: C.crema,
              fontFamily: "DM Sans, sans-serif",
              fontWeight: 600, fontSize: "0.9rem",
              cursor: guardandoPass ? "not-allowed" : "pointer",
              transition: "background 0.2s",
            }}
          >
            {guardandoPass ? "Guardando..." : "Actualizar contraseña"}
          </button>
        </form>
      </div>
    </div>
  );
}
