import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './components/AuthContext';
import Login from './pages/Login';
import Cultivos from './pages/Cultivos';
import Monitoreo from './pages/Monitoreo';
import InteligenciaArtificial from './pages/InteligenciaArtificial';
import Trazabilidad from './pages/Trazabilidad';
import Mercado from './pages/Mercado';
import Reportes from './pages/Reportes';

const RutaProtegida = ({ children }) => {
  const { estaAutenticado, cargando } = useAuth();
  if (cargando) return <div>Cargando...</div>;
  return estaAutenticado ? children : <Navigate to="/login" />;
};

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/cultivos" element={<RutaProtegida><Cultivos /></RutaProtegida>} />
      <Route path="/cultivo/dashboard" element={<RutaProtegida><Cultivos /></RutaProtegida>} />
      <Route path="/admin/dashboard" element={<RutaProtegida><Cultivos /></RutaProtegida>} />
      <Route path="/produccion/dashboard" element={<RutaProtegida><Cultivos /></RutaProtegida>} />
      <Route path="/monitoreo" element={<RutaProtegida><Monitoreo /></RutaProtegida>} />
      <Route path="/ia" element={<RutaProtegida><InteligenciaArtificial /></RutaProtegida>} />
      <Route path="/trazabilidad" element={<RutaProtegida><Trazabilidad /></RutaProtegida>} />
      <Route path="/trazabilidad/consulta" element={<RutaProtegida><Trazabilidad /></RutaProtegida>} />
      <Route path="/mercado" element={<RutaProtegida><Mercado /></RutaProtegida>} />
      <Route path="/mercado/dashboard" element={<RutaProtegida><Mercado /></RutaProtegida>} />
      <Route path="/reportes" element={<RutaProtegida><Reportes /></RutaProtegida>} />
      <Route path="/" element={<Navigate to="/login" />} />
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