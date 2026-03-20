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

function AppRoutes() {
  const { estaAutenticado, usuario } = useAuth();

  // Redirigir desde / según rol
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

      {/* Rutas legacy — redirigen a las nuevas */}
      <Route path="/admin/dashboard"     element={<Navigate to="/dashboard" replace />} />
      <Route path="/cultivo/dashboard"   element={<Navigate to="/cultivos" replace />} />
      <Route path="/produccion/dashboard" element={<Navigate to="/dashboard" replace />} />
      <Route path="/mercado/dashboard"   element={<Navigate to="/mercado" replace />} />
      <Route path="/trazabilidad/consulta" element={<Navigate to="/trazabilidad" replace />} />

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
