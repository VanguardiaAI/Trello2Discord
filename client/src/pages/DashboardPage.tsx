import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const DashboardPage = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    // Verificar si el usuario está autenticado
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/auth');
      return;
    }
    setIsAuthenticated(true);
  }, [navigate]);

  if (!isAuthenticated) {
    return <div>Verificando autenticación...</div>;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Panel de Control</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Integraciones</h2>
          <p className="text-gray-600 mb-4">
            Gestiona tus integraciones entre Trello y Discord.
          </p>
          <button 
            onClick={() => navigate('/integrations')}
            className="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded"
          >
            Ver Integraciones
          </button>
        </div>
        
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Mapeos de Usuarios</h2>
          <p className="text-gray-600 mb-4">
            Vincula usuarios de Trello con usuarios de Discord.
          </p>
          <button 
            onClick={() => navigate('/user-mappings')}
            className="bg-green-500 hover:bg-green-600 text-white font-medium py-2 px-4 rounded"
          >
            Gestionar Mapeos
          </button>
        </div>
      </div>
      
      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Mapeos de Listas</h2>
          <p className="text-gray-600 mb-4">
            Vincula manualmente listas de Trello con canales de Discord.
          </p>
          <button 
            onClick={() => navigate('/card-mappings')}
            className="bg-purple-500 hover:bg-purple-600 text-white font-medium py-2 px-4 rounded"
          >
            Gestionar Mapeos de Listas
          </button>
        </div>
        
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Configuración</h2>
          <p className="text-gray-600 mb-4">
            Configura las opciones de tu cuenta.
          </p>
          <button 
            onClick={() => navigate('/settings')}
            className="bg-gray-500 hover:bg-gray-600 text-white font-medium py-2 px-4 rounded"
          >
            Abrir Configuración
          </button>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage; 