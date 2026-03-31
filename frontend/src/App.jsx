// =============================================================
// frontend/src/App.jsx
//
// AUTH-001 FIX: rutas legacy ahora evalúan el rol antes de redirigir
// AUTH-002 FIX: ruta /perfil existía en menuConfig pero no en el router — agregada
// =============================================================

import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './components/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Cultivos from './pages/Cultivos';
import Monitoreo from './pages/Monitoreo';
import InteligenciaArtificial from './pages/InteligenciaArtificial';
import Trazabilidad from './pages/Trazabilidad';
import Mercado from './pages/Mercado';
import Reportes from './pages/Reportes';
import Perfil from './pages/Perfil';

// ── Ruta protegida con Layout ─────────────────────────────────
const RutaProtegida = ({ children }) => {
  const { estaAutenticado, cargando } = useAuth();
  const location = useLocation();

  if (cargando) return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '100vh', background: '#F5ECD7',
      fontFamily: 'DM Sans, sans-serif', color: '#5C3317', fontSize: 16
    }}>
      Cargando...
    </div>
  );

  if (!estaAutenticado) return <Navigate to="/login" state={{ from: location }} replace />;

  return (
    <Layout currentPath={location.pathname}>
      {children}
    </Layout>
  );
};

// AUTH-001 FIX: ruta legacy con verificación de rol
const RutaLegacy = ({ rolEsperado, destino }) => {
  const { estaAutenticado, usuario } = useAuth();

  if (!estaAutenticado) return <Navigate to="/login" replace />;

  const rolActual = usuario?.rol?.nombre_rol;

  // Solo redirigir a la ruta legacy si el rol coincide
  if (rolEsperado && rolActual !== rolEsperado && rolActual !== "Administrador") {
    return <Navigate to="/dashboard" replace />;
  }

  return <Navigate to={destino} replace />;
};

function AppRoutes() {
  const { estaAutenticado, usuario } = useAuth();

  const getDashboardPath = () => {
    const rol = usuario?.rol?.nombre_rol;
    if (rol === "Comercializador") return "/mercado";
    if (rol === "Consumidor")      return "/trazabilidad";
    return "/dashboard";
  };

  return (
    <Routes>
      <Route path="/login" element={
        estaAutenticado ? <Navigate to={getDashboardPath()} replace /> : <Login />
      } />

      <Route path="/dashboard"    element={<RutaProtegida><Cultivos /></RutaProtegida>} />
      <Route path="/cultivos"     element={<RutaProtegida><Cultivos /></RutaProtegida>} />
      <Route path="/monitoreo"    element={<RutaProtegida><Monitoreo /></RutaProtegida>} />
      <Route path="/ia"           element={<RutaProtegida><InteligenciaArtificial /></RutaProtegida>} />
      <Route path="/trazabilidad" element={<RutaProtegida><Trazabilidad /></RutaProtegida>} />
      <Route path="/mercado"      element={<RutaProtegida><Mercado /></RutaProtegida>} />
      <Route path="/reportes"     element={<RutaProtegida><Reportes /></RutaProtegida>} />
      {/* AUTH-002 FIX: ruta /perfil existía en menuConfig pero faltaba en el router */}
      <Route path="/perfil"       element={<RutaProtegida><Perfil /></RutaProtegida>} />

      {/* AUTH-001 FIX: rutas legacy verifican rol antes de redirigir */}
      <Route path="/admin/dashboard"
        element={<RutaLegacy rolEsperado="Administrador" destino="/dashboard" />} />
      <Route path="/cultivo/dashboard"
        element={<RutaLegacy rolEsperado="Caficultor" destino="/cultivos" />} />
      <Route path="/produccion/dashboard"
        element={<RutaLegacy rolEsperado="Productor" destino="/dashboard" />} />
      <Route path="/mercado/dashboard"
        element={<RutaLegacy rolEsperado="Comercializador" destino="/mercado" />} />
      <Route path="/trazabilidad/consulta"
        element={<RutaLegacy rolEsperado="Consumidor" destino="/trazabilidad" />} />

      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
