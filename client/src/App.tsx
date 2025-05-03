import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthPage } from './pages/AuthPage';
import IntegrationsPage from './pages/IntegrationsPage';
import UserMappingsPage from './pages/UserMappingsPage';
import CardMappingsPage from './pages/CardMappingsPage';
// import ProfilePage from './pages/ProfilePage';
import SettingsPage from './pages/SettingsPage';
import DebugPage from './pages/DebugPage';
import LeadsPage from './pages/LeadsPage';
import Layout from './components/Layout';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/auth" element={<AuthPage />} />
        
        {/* Rutas protegidas con Layout */}
        <Route path="/" element={<Layout><IntegrationsPage /></Layout>} />
        <Route path="/integration/:integrationId/user-mappings" element={<Layout><UserMappingsPage /></Layout>} />
        <Route path="/integration/:integrationId/card-mappings" element={<Layout><CardMappingsPage /></Layout>} />
        {/* <Route path="/profile" element={<Layout><ProfilePage /></Layout>} /> */}
        <Route path="/settings" element={<Layout><SettingsPage /></Layout>} />
        <Route path="/debug" element={<Layout><DebugPage /></Layout>} />
        <Route path="/leads" element={<Layout><LeadsPage /></Layout>} />
        
        {/* Redirigir cualquier ruta desconocida a la página principal */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
