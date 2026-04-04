// =============================================================
// frontend/src/components/Layout.jsx
// Sidebar + Navbar — GranoVital IA
// RN-01: navegación filtrada por rol
// =============================================================

import { useState, useEffect, useRef } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "./AuthContext";
import { getMenuPorRol } from "./menuConfig";
import {
  LogOut,
  Menu,
  X,
  ChevronRight,
  Coffee,
} from "lucide-react";

// ── Paleta de colores café/tierra ────────────────────────────
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
  }

  /* ── Layout contenedor ── */
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

  /* Logo */
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

  /* Rol badge */
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

  /* Nav items */
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

  /* Logout */
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

  /* Breadcrumb / título de página */
  .gv-page-title {
    font-family: 'Playfair Display', serif;
    font-size: 18px;
    color: var(--cafe-oscuro);
    font-weight: 600;
  }

  .gv-navbar-spacer { flex: 1; }

  /* Avatar usuario */
  .gv-user-dropdown {
    position: relative;
    display: inline-flex;
    align-items: center;
    z-index: 1000;
  }

  .gv-user-info {
    display: flex;
    align-items: center;
    gap: 10px;
    border: 1px solid transparent;
    background: rgba(255,255,255,0.75);
    border-radius: 10px;
    padding: 8px 12px;
    cursor: pointer;
    min-width: 180px;
    transition: background var(--transition), border-color var(--transition), box-shadow var(--transition);
  }

  .gv-user-info:hover,
  .gv-user-info.active {
    background: rgba(255,255,255,0.95);
    border-color: var(--cafe-claro);
    box-shadow: 0 8px 24px rgba(0,0,0,0.18);
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
    user-select: none;
  }

  .gv-dropdown-menu {
    position: absolute;
    top: calc(100% + 10px);
    right: 0;
    background: white;
    border: 1px solid rgba(92,51,23,0.15);
    border-radius: 10px;
    box-shadow: 0 8px 20px rgba(0,0,0,0.2);
    min-width: 160px;
    padding: 0.4rem 0;
    overflow: hidden;
    animation: dropdownFade 0.2s ease;
  }

  .gv-dropdown-item {
    display: block;
    width: 100%;
    text-align: left;
    padding: 0.6rem 0.9rem;
    background: transparent;
    border: none;
    color: var(--cafe-oscuro);
    font-size: 0.9rem;
    text-decoration: none;
    cursor: pointer;
    font-weight: 500;
  }

  .gv-dropdown-item:hover {
    background: var(--crema);
  }

  @keyframes dropdownFade {
    from { opacity: 0; transform: translateY(-5px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  /* ── CONTENIDO PRINCIPAL ── */
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

  /* ── OVERLAY móvil ── */
  .gv-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.5);
    z-index: 99;
  }

  /* ── Responsive ── */
  @media (max-width: 768px) {
    .gv-navbar { left: 0 !important; }
    .gv-main   { margin-left: 0 !important; }
    .gv-overlay.visible { display: block; }
  }
`;

// ── Nombres de página por ruta ────────────────────────────────
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

// ── Componente principal ──────────────────────────────────────
export default function Layout({ children, currentPath = "/" }) {
  const { usuario, logout, tieneRol, bienvenida } = useAuth();  // F-L08
  const navigate = useNavigate();
  const [sidebarAbierto, setSidebarAbierto] = useState(true);
  const [perfilMenuVisible, setPerfilMenuVisible] = useState(false);
  const perfilMenuRef = useRef(null);

  const rol = usuario?.rol?.nombre_rol || "";
  const menuItems = getMenuPorRol(rol);
  const pageTitle = PAGE_TITLES[currentPath] || "GranoVital IA";

  // Inicial del nombre para el avatar
  const inicial = usuario?.nombre
    ? usuario.nombre.charAt(0).toUpperCase()
    : "U";

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  const toggleSidebar = () => setSidebarAbierto((v) => !v);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (perfilMenuRef.current && !perfilMenuRef.current.contains(event.target)) {
        setPerfilMenuVisible(false);
      }
    };

    if (perfilMenuVisible) {
      document.addEventListener("mousedown", handleClickOutside);
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [perfilMenuVisible]);

  return (
    <>
      <style>{styles}</style>

      <div className="gv-layout">
        {/* ── Overlay móvil ── */}
        <div
          className={`gv-overlay ${sidebarAbierto ? "visible" : ""}`}
          onClick={toggleSidebar}
        />

        {/* ── SIDEBAR ── */}
        <aside className={`gv-sidebar ${sidebarAbierto ? "" : "collapsed"}`}>
          {/* Logo */}
          <div className="gv-sidebar-logo">
            <div className="gv-logo-icon">
              <Coffee size={18} color="#F5ECD7" />
            </div>
            <div>
              <div className="gv-logo-text">GranoVital</div>
              <div className="gv-logo-sub">IA · Gestión Café</div>
            </div>
          </div>

          {/* Badge de rol */}
          {rol && <div className="gv-rol-badge">{rol}</div>}

          {/* Navegación */}
          <nav className="gv-nav">
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
                  <Icon size={18} />
                  <span>{item.label}</span>
                  <ChevronRight size={14} className="gv-nav-arrow" />
                </NavLink>
              );
            })}
          </nav>

          {/* Footer con logout */}
          <div className="gv-sidebar-footer">
            <button className="gv-logout-btn" onClick={handleLogout}>
              <LogOut size={18} />
              <span>Cerrar sesión</span>
            </button>
          </div>
        </aside>

        {/* ── NAVBAR ── */}
        <header className={`gv-navbar ${sidebarAbierto ? "" : "sidebar-collapsed"}`}>
          <button className="gv-toggle-btn" onClick={toggleSidebar}>
            {sidebarAbierto ? <X size={18} /> : <Menu size={18} />}
          </button>

          <span className="gv-page-title">{pageTitle}</span>

          <div className="gv-navbar-spacer" />

          <div className="gv-user-dropdown" ref={perfilMenuRef}>
            <button
              className={`gv-user-info ${perfilMenuVisible ? "active" : ""}`}
              onClick={() => setPerfilMenuVisible((open) => !open)}
              aria-haspopup="true"
              aria-expanded={perfilMenuVisible}
            >
              <div>
                <div className="gv-user-name">{usuario?.nombre || "Usuario"}</div>
                <div className="gv-user-rol">{rol}</div>
              </div>
              <div className="gv-avatar">{inicial}</div>
            </button>

            {perfilMenuVisible && (
              <div className="gv-dropdown-menu">
                <NavLink
                  to="/perfil"
                  className="gv-dropdown-item"
                  onClick={() => setPerfilMenuVisible(false)}
                >
                  Perfil
                </NavLink>
                <button
                  className="gv-dropdown-item"
                  onClick={async () => {
                    setPerfilMenuVisible(false);
                    await handleLogout();
                  }}
                >
                  Cerrar sesión
                </button>
              </div>
            )}
          </div>
        </header>

        {/* F-L08: toast de bienvenida */}
        {bienvenida && (
          <div style={{
            position: "fixed", bottom: "24px", left: "50%",
            transform: "translateX(-50%)", zIndex: 9999,
            background: "var(--cafe-oscuro)", color: "var(--crema)",
            padding: "12px 28px", borderRadius: "50px",
            fontWeight: 600, fontSize: "15px",
            boxShadow: "0 4px 20px rgba(0,0,0,0.3)",
            animation: "fadeIn 0.3s ease",
          }}>
            {bienvenida}
          </div>
        )}

        {/* ── CONTENIDO ── */}
        <main className={`gv-main ${sidebarAbierto ? "" : "sidebar-collapsed"}`}>
          {children}
        </main>
      </div>
    </>
  );
}
