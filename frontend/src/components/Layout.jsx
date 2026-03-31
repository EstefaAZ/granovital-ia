// =============================================================
// frontend/src/components/Layout.jsx
// Sidebar + Navbar — GranoVital IA
// RN-01: navegación filtrada por rol
//
// QA FIXES sobre la versión original del proyecto:
//   UX-004 FIX: body sin text-align:center — #root ya no tiene width fijo
//   OFF-002 FIX: badge de pendientes offline en navbar
//   Accesibilidad: aria-label en botones de toggle y nav
// =============================================================

import { useState, useRef, useEffect } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { getMenuPorRol } from "./menuConfig";
import { useOfflineSync } from "../hooks/useOfflineSync";
import {
  LogOut,
  Menu,
  X,
  ChevronRight,
  Coffee,
  User,
  Settings,
  ChevronDown,
  WifiOff,
} from "lucide-react";

const styles = `
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=DM+Sans:wght@300;400;500&display=swap');

  :root {
    --cafe-oscuro:   #2C1A0E;
    --cafe-medio:    #5C3317;
    --cafe-claro:    #8B5E3C;
    --cafe-suave:    #C49A6C;
    --crema:         #F5ECD7;
    --crema-oscura:  #EAD9BF;
    --verde-hoja:    #4A7C59;
    --texto-oscuro:  #1A0F07;
    --texto-medio:   #5C3317;
    --sidebar-w:     260px;
    --navbar-h:      64px;
    --transition:    0.25s cubic-bezier(0.4, 0, 0.2, 1);
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'DM Sans', sans-serif;
    background: var(--crema);
    color: var(--texto-oscuro);
    /* UX-004 FIX: sin text-align:center global que desalineaba el sidebar */
    text-align: left;
  }

  .gv-layout {
    display: flex;
    min-height: 100vh;
  }

  /* ── SIDEBAR ── */
  .gv-sidebar {
    position: fixed;
    top: 0; left: 0;
    width: var(--sidebar-w);
    height: 100vh;
    background: var(--cafe-oscuro);
    display: flex;
    flex-direction: column;
    z-index: 100;
    transition: transform var(--transition);
    overflow: hidden;
  }

  .gv-sidebar::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 200px; height: 200px;
    background: radial-gradient(circle, rgba(140,94,60,0.3) 0%, transparent 70%);
    pointer-events: none;
  }

  .gv-sidebar.collapsed {
    transform: translateX(calc(-1 * var(--sidebar-w)));
  }

  .gv-sidebar-logo {
    padding: 24px 20px 20px;
    border-bottom: 1px solid rgba(196,154,108,0.2);
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .gv-logo-icon {
    width: 36px; height: 36px;
    background: linear-gradient(135deg, var(--cafe-claro), var(--cafe-suave));
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .gv-logo-text {
    font-family: 'Playfair Display', serif;
    font-size: 18px;
    font-weight: 700;
    color: var(--crema);
    line-height: 1.1;
  }

  .gv-logo-sub {
    font-size: 10px;
    color: var(--cafe-suave);
    font-weight: 300;
    letter-spacing: 1.5px;
    text-transform: uppercase;
  }

  .gv-rol-badge {
    margin: 16px 20px 8px;
    padding: 6px 12px;
    background: rgba(196,154,108,0.15);
    border: 1px solid rgba(196,154,108,0.25);
    border-radius: 20px;
    font-size: 11px;
    color: var(--cafe-suave);
    letter-spacing: 0.5px;
    text-align: center;
  }

  .gv-nav {
    flex: 1;
    padding: 8px 12px;
    overflow-y: auto;
    scrollbar-width: none;
  }

  .gv-nav::-webkit-scrollbar { display: none; }

  .gv-nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 11px 14px;
    border-radius: 10px;
    color: rgba(245,236,215,0.65);
    text-decoration: none;
    font-size: 14px;
    font-weight: 400;
    transition: all var(--transition);
    margin-bottom: 2px;
    position: relative;
    overflow: hidden;
  }

  .gv-nav-item::before {
    content: '';
    position: absolute;
    left: 0; top: 0;
    width: 3px; height: 100%;
    background: var(--cafe-suave);
    border-radius: 0 3px 3px 0;
    transform: scaleY(0);
    transition: transform var(--transition);
  }

  .gv-nav-item:hover {
    background: rgba(196,154,108,0.12);
    color: var(--crema);
  }

  .gv-nav-item.active {
    background: rgba(196,154,108,0.2);
    color: var(--crema);
    font-weight: 500;
  }

  .gv-nav-item.active::before {
    transform: scaleY(1);
  }

  .gv-nav-item svg {
    flex-shrink: 0;
    opacity: 0.8;
  }

  .gv-nav-item.active svg,
  .gv-nav-item:hover svg {
    opacity: 1;
  }

  .gv-nav-arrow {
    margin-left: auto;
    opacity: 0;
    transition: opacity var(--transition), transform var(--transition);
  }

  .gv-nav-item:hover .gv-nav-arrow,
  .gv-nav-item.active .gv-nav-arrow {
    opacity: 1;
    transform: translateX(2px);
  }

  .gv-sidebar-footer {
    padding: 12px;
    border-top: 1px solid rgba(196,154,108,0.2);
  }

  .gv-logout-btn {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 11px 14px;
    border-radius: 10px;
    background: none;
    border: none;
    color: rgba(245,236,215,0.5);
    font-size: 14px;
    font-family: 'DM Sans', sans-serif;
    cursor: pointer;
    transition: all var(--transition);
  }

  .gv-logout-btn:hover {
    background: rgba(220,60,60,0.15);
    color: #ff8080;
  }

  /* ── NAVBAR ── */
  .gv-navbar {
    position: fixed;
    top: 0;
    left: var(--sidebar-w);
    right: 0;
    height: var(--navbar-h);
    background: rgba(245,236,215,0.92);
    backdrop-filter: blur(12px);
    border-bottom: 1px solid var(--crema-oscura);
    display: flex;
    align-items: center;
    padding: 0 24px;
    z-index: 99;
    transition: left var(--transition);
    gap: 16px;
  }

  .gv-navbar.sidebar-collapsed {
    left: 0;
  }

  .gv-toggle-btn {
    width: 36px; height: 36px;
    border-radius: 8px;
    border: 1px solid var(--crema-oscura);
    background: white;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    color: var(--cafe-medio);
    transition: all var(--transition);
    flex-shrink: 0;
  }

  .gv-toggle-btn:hover {
    background: var(--crema-oscura);
  }

  .gv-page-title {
    font-family: 'Playfair Display', serif;
    font-size: 18px;
    color: var(--cafe-oscuro);
    font-weight: 600;
  }

  .gv-navbar-spacer { flex: 1; }

  /* ── DROPDOWN PERFIL ── */
  .gv-user-trigger {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
    padding: 6px 10px 6px 6px;
    border-radius: 24px;
    border: 1px solid transparent;
    transition: all var(--transition);
    user-select: none;
    position: relative;
  }

  .gv-user-trigger:hover {
    background: var(--crema-oscura);
    border-color: var(--crema-oscura);
  }

  .gv-user-name {
    font-size: 13px;
    font-weight: 500;
    color: var(--cafe-medio);
    text-align: right;
    line-height: 1.2;
  }

  .gv-user-rol {
    font-size: 11px;
    color: var(--cafe-claro);
    font-weight: 300;
  }

  .gv-avatar {
    width: 36px; height: 36px;
    background: linear-gradient(135deg, var(--cafe-medio), var(--cafe-claro));
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--crema);
    font-family: 'Playfair Display', serif;
    font-size: 14px;
    font-weight: 600;
    flex-shrink: 0;
  }

  .gv-chevron {
    color: var(--cafe-claro);
    transition: transform var(--transition);
    flex-shrink: 0;
  }

  .gv-chevron.open {
    transform: rotate(180deg);
  }

  /* Dropdown menu */
  .gv-dropdown {
    position: absolute;
    top: calc(100% + 8px);
    right: 0;
    width: 220px;
    background: #fff;
    border: 1px solid var(--crema-oscura);
    border-radius: 12px;
    box-shadow: 0 8px 24px rgba(44,26,14,0.12);
    overflow: hidden;
    z-index: 200;
    animation: dropIn 0.15s ease;
  }

  @keyframes dropIn {
    from { opacity: 0; transform: translateY(-6px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  .gv-dropdown-header {
    padding: 14px 16px 10px;
    border-bottom: 1px solid var(--crema-oscura);
  }

  .gv-dropdown-nombre {
    font-size: 13px;
    font-weight: 600;
    color: var(--cafe-oscuro);
  }

  .gv-dropdown-correo {
    font-size: 11px;
    color: var(--cafe-claro);
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .gv-dropdown-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 16px;
    font-size: 13px;
    color: var(--cafe-medio);
    cursor: pointer;
    transition: background var(--transition);
    border: none;
    background: none;
    width: 100%;
    text-align: left;
    font-family: 'DM Sans', sans-serif;
    text-decoration: none;
  }

  .gv-dropdown-item:hover {
    background: var(--crema);
  }

  .gv-dropdown-item svg {
    opacity: 0.7;
    flex-shrink: 0;
  }

  .gv-dropdown-divider {
    height: 1px;
    background: var(--crema-oscura);
    margin: 4px 0;
  }

  .gv-dropdown-item.danger {
    color: #B91C1C;
  }

  .gv-dropdown-item.danger svg {
    opacity: 1;
  }

  .gv-dropdown-item.danger:hover {
    background: #FEF2F2;
  }

  /* ── MAIN ── */
  .gv-main {
    margin-left: var(--sidebar-w);
    margin-top: var(--navbar-h);
    min-height: calc(100vh - var(--navbar-h));
    padding: 28px;
    transition: margin-left var(--transition);
    background: var(--crema);
  }

  .gv-main.sidebar-collapsed {
    margin-left: 0;
  }

  .gv-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.5);
    z-index: 99;
  }

  @media (max-width: 768px) {
    .gv-navbar { left: 0 !important; }
    .gv-main   { margin-left: 0 !important; padding: 16px; }
    .gv-overlay.visible { display: block; }
  }
`;

const PAGE_TITLES = {
  "/dashboard":    "Dashboard",
  "/cultivos":     "Mis Cultivos",
  "/monitoreo":    "Monitoreo Ambiental",
  "/ia":           "Inteligencia Artificial",
  "/trazabilidad": "Trazabilidad",
  "/mercado":      "Mercado",
  "/reportes":     "Reportes",
  "/perfil":       "Mi Perfil",
};

export default function Layout({ children, currentPath = "/" }) {
  const { usuario, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarAbierto, setSidebarAbierto] = useState(true);
  const [dropdownAbierto, setDropdownAbierto] = useState(false);
  const dropdownRef = useRef(null);

  // OFF-002 FIX: badge de registros pendientes de sincronización offline
  const { pendientes, sincronizando } = useOfflineSync();

  const rol = usuario?.rol?.nombre_rol || "";

  // Filtrar "perfil" del menú lateral — va solo en el dropdown
  const menuItems = getMenuPorRol(rol).filter(item => item.key !== "perfil");

  const pageTitle = PAGE_TITLES[currentPath] || "GranoVital IA";
  const inicial = usuario?.nombre?.charAt(0).toUpperCase() || "U";
  const nombreCompleto = `${usuario?.nombre || ""} ${usuario?.apellido || ""}`.trim();

  // Cerrar dropdown al hacer click fuera
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownAbierto(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleLogout = async () => {
    setDropdownAbierto(false);
    await logout();
    navigate("/login");
  };

  const irA = (path) => {
    setDropdownAbierto(false);
    navigate(path);
  };

  return (
    <>
      <style>{styles}</style>

      <div className="gv-layout">
        <div
          className={`gv-overlay ${sidebarAbierto ? "visible" : ""}`}
          onClick={() => setSidebarAbierto(false)}
        />

        {/* ── SIDEBAR ── */}
        <aside className={`gv-sidebar ${sidebarAbierto ? "" : "collapsed"}`}
          aria-label="Menú de navegación principal">
          <div className="gv-sidebar-logo">
            <div className="gv-logo-icon" aria-hidden="true">
              <Coffee size={18} color="#F5ECD7" />
            </div>
            <div>
              <div className="gv-logo-text">GranoVital</div>
              <div className="gv-logo-sub">IA · Gestión Café</div>
            </div>
          </div>

          {rol && <div className="gv-rol-badge">{rol}</div>}

          <nav className="gv-nav" aria-label="Módulos del sistema">
            {menuItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.key}
                  to={item.path}
                  className={({ isActive }) =>
                    `gv-nav-item ${isActive ? "active" : ""}`
                  }
                  onClick={() => {
                    if (window.innerWidth <= 768) setSidebarAbierto(false);
                  }}
                >
                  <Icon size={18} aria-hidden="true" />
                  <span>{item.label}</span>
                  <ChevronRight size={14} className="gv-nav-arrow" aria-hidden="true" />
                </NavLink>
              );
            })}
          </nav>

          <div className="gv-sidebar-footer">
            <button className="gv-logout-btn" onClick={handleLogout}>
              <LogOut size={18} aria-hidden="true" />
              <span>Cerrar sesión</span>
            </button>
          </div>
        </aside>

        {/* ── NAVBAR ── */}
        <header className={`gv-navbar ${sidebarAbierto ? "" : "sidebar-collapsed"}`}>
          <button
            className="gv-toggle-btn"
            onClick={() => setSidebarAbierto(v => !v)}
            aria-label={sidebarAbierto ? "Ocultar menú lateral" : "Mostrar menú lateral"}
            aria-expanded={sidebarAbierto}
          >
            {sidebarAbierto ? <X size={18} /> : <Menu size={18} />}
          </button>

          <span className="gv-page-title">{pageTitle}</span>

          {/* OFF-002 FIX: badge de registros pendientes offline */}
          {pendientes > 0 && (
            <div
              style={{
                display: "flex", alignItems: "center", gap: "6px",
                background: "#fffbeb", border: "1px solid #c8a000",
                borderRadius: "20px", padding: "4px 10px",
                fontSize: "12px", color: "#92400e", flexShrink: 0,
              }}
              title={`${pendientes} registro(s) pendiente(s) de sincronizar cuando haya conexión`}
              role="status"
              aria-live="polite"
            >
              <WifiOff size={13} aria-hidden="true" />
              {sincronizando ? "Sincronizando..." : `${pendientes} pendiente(s)`}
            </div>
          )}

          <div className="gv-navbar-spacer" />

          {/* Avatar con dropdown */}
          <div ref={dropdownRef} style={{ position: "relative" }}>
            <div
              className="gv-user-trigger"
              onClick={() => setDropdownAbierto(v => !v)}
              role="button"
              aria-haspopup="true"
              aria-expanded={dropdownAbierto}
              aria-label={`Menú de usuario: ${nombreCompleto || "Usuario"}`}
            >
              <div>
                <div className="gv-user-name">{nombreCompleto || "Usuario"}</div>
                <div className="gv-user-rol">{rol}</div>
              </div>
              <div className="gv-avatar" aria-hidden="true">{inicial}</div>
              <ChevronDown
                size={14}
                className={`gv-chevron ${dropdownAbierto ? "open" : ""}`}
                aria-hidden="true"
              />
            </div>

            {/* Dropdown */}
            {dropdownAbierto && (
              <div className="gv-dropdown" role="menu" aria-label="Opciones de usuario">
                <div className="gv-dropdown-header">
                  <div className="gv-dropdown-nombre">{nombreCompleto}</div>
                  <div className="gv-dropdown-correo">{usuario?.correo}</div>
                </div>

                <button
                  className="gv-dropdown-item"
                  onClick={() => irA("/perfil")}
                  role="menuitem"
                >
                  <User size={15} aria-hidden="true" />
                  Mi perfil
                </button>

                <div className="gv-dropdown-divider" role="separator" />

                <button
                  className="gv-dropdown-item danger"
                  onClick={handleLogout}
                  role="menuitem"
                >
                  <LogOut size={15} aria-hidden="true" />
                  Cerrar sesión
                </button>
              </div>
            )}
          </div>
        </header>

        {/* ── CONTENIDO ── */}
        <main
          className={`gv-main ${sidebarAbierto ? "" : "sidebar-collapsed"}`}
          id="main-content"
        >
          {children}
        </main>
      </div>
    </>
  );
}
