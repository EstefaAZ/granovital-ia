// ==============================================================
// frontend/src/components/Modal.jsx
// Componente Modal compartido — accesible y reutilizable
//
// UX-001 FIX: cierre con tecla Escape (WCAG 2.1 criterio 2.1.1)
// UX-002 FIX: aria-label descriptivo en el botón de cierre
// ==============================================================

import { useEffect } from "react";

const COLOR_CAFE = "#6f3a1b";

export default function Modal({ abierto, titulo, onCerrar, children }) {
  // UX-001 FIX: cerrar con Escape (accesibilidad de teclado)
  useEffect(() => {
    if (!abierto) return;
    const manejarTeclado = (e) => {
      if (e.key === "Escape") onCerrar();
    };
    document.addEventListener("keydown", manejarTeclado);
    return () => document.removeEventListener("keydown", manejarTeclado);
  }, [abierto, onCerrar]);

  // Bloquear scroll del body mientras el modal está abierto
  useEffect(() => {
    if (abierto) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => { document.body.style.overflow = ""; };
  }, [abierto]);

  if (!abierto) return null;

  return (
    <div
      style={{
        position:       "fixed",
        inset:          0,
        background:     "rgba(0,0,0,0.4)",
        display:        "flex",
        alignItems:     "center",
        justifyContent: "center",
        zIndex:         1000,
        padding:        "1rem",
      }}
      // Cierre al hacer clic en el fondo (backdrop)
      onClick={(e) => { if (e.target === e.currentTarget) onCerrar(); }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-titulo"
    >
      <div
        style={{
          background:   "#fff",
          borderRadius: "16px",
          padding:      "2rem",
          width:        "100%",
          maxWidth:     "520px",
          maxHeight:    "90vh",
          overflowY:    "auto",
          boxShadow:    "0 20px 60px rgba(0,0,0,0.3)",
        }}
        // Prevenir que los clicks dentro del modal lo cierren
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
          <h3 id="modal-titulo" style={{ margin: 0, color: COLOR_CAFE }}>{titulo}</h3>
          {/* UX-002 FIX: aria-label descriptivo en el botón de cierre */}
          <button
            onClick={onCerrar}
            aria-label="Cerrar modal"
            style={{
              background:   "none",
              border:       "1.5px solid #e0d5c9",
              borderRadius: "8px",
              width:        "32px",
              height:       "32px",
              display:      "flex",
              alignItems:   "center",
              justifyContent: "center",
              cursor:       "pointer",
              color:        "#7a5c3a",
              fontSize:     "1rem",
              flexShrink:   0,
              transition:   "background 0.15s",
            }}
            onMouseEnter={e => e.currentTarget.style.background = "#f5f0eb"}
            onMouseLeave={e => e.currentTarget.style.background = "none"}
          >
            {/* SVG ✕ en lugar del carácter 'x' para mejor renderizado */}
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
              <path d="M1 1L13 13M13 1L1 13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
