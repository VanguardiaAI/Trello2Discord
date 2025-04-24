import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ConfirmDialog } from '../components/ui/confirm-dialog';
import { Alert } from '../components/ui/alert';

interface Integration {
  _id: string;
  trello_board_id: string;
  discord_server_id: string;
  webhook_id: string;
  created_at: string;
  updated_at: string;
  active: boolean;
}

interface TrelloBoard {
  id: string;
  name: string;
  url: string;
  closed: boolean;
  description: string;
}

interface MonitoringStatus {
  active: boolean;
  monitored_board_id: string | null;
}

const IntegrationsPage = () => {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Estado para manejar tableros de Trello
  const [trelloBoards, setTrelloBoards] = useState<TrelloBoard[]>([]);
  const [loadingBoards, setLoadingBoards] = useState(false);
  const [boardsError, setBoardsError] = useState<string | null>(null);
  
  // Estado para monitoreo de Trello
  const [monitoringStatus, setMonitoringStatus] = useState<MonitoringStatus>({ active: false, monitored_board_id: null });
  const [loadingMonitoring, setLoadingMonitoring] = useState(false);
  const [monitoringError, setMonitoringError] = useState<string | null>(null);
  
  const [selectedBoardId, setSelectedBoardId] = useState('');
  const [discordServerId, setDiscordServerId] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  
  // Agregar un estado para manejar la eliminación en progreso
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | undefined>(undefined);
  
  const [globalAlert, setGlobalAlert] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  
  const navigate = useNavigate();

  useEffect(() => {
    // Verificar autenticación
    const token = localStorage.getItem('token');
    
    // Cargar tableros de Trello independientemente de la autenticación
    fetchTrelloBoards();
    
    // Solo intentar cargar integraciones si hay un token
    if (token) {
      fetchIntegrations();
      fetchMonitoringStatus();
    }
  }, [navigate]);

  const fetchTrelloBoards = async () => {
    try {
      setLoadingBoards(true);
      setBoardsError(null);
      
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/debug/trello/boards`);
      const data = await response.json();
      
      if (data.status === 'success') {
        setTrelloBoards(data.boards);
      } else {
        setBoardsError(data.message || 'Error al obtener tableros de Trello');
      }
    } catch (err) {
      setBoardsError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoadingBoards(false);
    }
  };

  const fetchMonitoringStatus = async () => {
    try {
      setLoadingMonitoring(true);
      setMonitoringError(null);
      
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/debug/trello/monitoring-status`);
      const data = await response.json();
      
      if (data.status === 'success') {
        setMonitoringStatus({
          active: data.active,
          monitored_board_id: data.monitored_board_id
        });
      } else {
        setMonitoringError(data.message || 'Error al obtener estado de monitoreo');
      }
    } catch (err) {
      setMonitoringError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoadingMonitoring(false);
    }
  };

  const handleStartMonitoring = async (boardId: string) => {
    try {
      setLoadingMonitoring(true);
      setMonitoringError(null);
      
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/debug/trello/start-monitoring/${boardId}`, {
        method: 'POST'
      });
      
      const data = await response.json();
      
      if (data.status === 'success') {
        setMonitoringStatus({
          active: true,
          monitored_board_id: boardId
        });
        setGlobalAlert({ type: 'success', message: `Monitoreo iniciado para el tablero "${getBoardName(boardId)}"` });
      } else {
        setMonitoringError(data.message || 'Error al iniciar monitoreo');
        setGlobalAlert({ type: 'error', message: `Error al iniciar monitoreo: ${data.message}` });
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Error desconocido';
      setMonitoringError(errorMsg);
      setGlobalAlert({ type: 'error', message: `Error al iniciar monitoreo: ${errorMsg}` });
    } finally {
      setLoadingMonitoring(false);
    }
  };

  const handleStopMonitoring = async () => {
    try {
      setLoadingMonitoring(true);
      setMonitoringError(null);
      
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/debug/trello/stop-monitoring`, {
        method: 'POST'
      });
      
      const data = await response.json();
      
      if (data.status === 'success') {
        setMonitoringStatus({
          active: false,
          monitored_board_id: null
        });
        setGlobalAlert({ type: 'success', message: 'Monitoreo detenido correctamente' });
      } else {
        setMonitoringError(data.message || 'Error al detener monitoreo');
        setGlobalAlert({ type: 'error', message: `Error al detener monitoreo: ${data.message}` });
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Error desconocido';
      setMonitoringError(errorMsg);
      setGlobalAlert({ type: 'error', message: `Error al detener monitoreo: ${errorMsg}` });
    } finally {
      setLoadingMonitoring(false);
    }
  };

  const fetchIntegrations = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setError('No hay token de autenticación. Por favor, inicia sesión.');
        setLoading(false);
        return;
      }

      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/integration/`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.status === 401) {
        setError('Sesión inválida o expirada. Por favor, inicia sesión nuevamente.');
        setLoading(false);
        return;
      }

      if (!response.ok) {
        throw new Error(`Error al cargar integraciones: ${response.status}`);
      }

      const data = await response.json();
      console.log("Integraciones recibidas:", data);
      
      // Filtrar integraciones con IDs válidos
      const validIntegrations = data.filter((integration: any) => {
        const isValid = integration._id && 
                        integration._id !== 'None' && 
                        integration._id !== 'undefined' && 
                        integration._id.trim() !== '';
        
        if (!isValid) {
          console.warn('Integración con ID inválido detectada:', integration);
        }
        
        return isValid;
      });
      
      if (validIntegrations.length !== data.length) {
        console.warn(`Se filtraron ${data.length - validIntegrations.length} integraciones con IDs inválidos`);
      }
      
      setIntegrations(validIntegrations);
    } catch (err) {
      console.error('Error al obtener integraciones:', err);
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateIntegration = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Validaciones mejoradas
    if (!selectedBoardId || selectedBoardId.trim() === '') {
      setCreateError('Debes seleccionar un tablero de Trello');
      return;
    }
    
    if (!discordServerId || discordServerId.trim() === '') {
      setCreateError('Debes proporcionar un ID de servidor de Discord válido');
      return;
    }
    
    // Validar que el ID de Discord tenga un formato numérico
    if (!/^\d+$/.test(discordServerId)) {
      setCreateError('El ID del servidor de Discord debe contener solo números');
      return;
    }
    
    try {
      setIsCreating(true);
      setCreateError(null);
      
      const token = localStorage.getItem('token');
      if (!token) {
        setCreateError('No hay token de autenticación. Por favor, inicia sesión.');
        setIsCreating(false);
        return;
      }
      
      // Obtener información del tablero seleccionado para mostrar mejor información
      const selectedBoard = trelloBoards.find(board => board.id === selectedBoardId);
      
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/integration/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          trello_board_id: selectedBoardId,
          discord_server_id: discordServerId,
          trello_board_name: selectedBoard?.name || '',
          trello_board_url: selectedBoard?.url || ''
        })
      });
      
      // Manejar diferentes códigos de estado
      if (response.status === 401) {
        setCreateError('Sesión inválida o expirada. Por favor, inicia sesión nuevamente.');
        setIsCreating(false);
        return;
      }
      
      if (response.status === 409) {
        setCreateError('Ya existe una integración para este tablero y servidor de Discord');
        setIsCreating(false);
        return;
      }
      
      if (response.status === 400) {
        const errorData = await response.json();
        setCreateError(errorData.message || 'Error en los datos proporcionados');
        setIsCreating(false);
        return;
      }
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Error al procesar la respuesta del servidor' }));
        throw new Error(errorData.message || 'Error al crear la integración');
      }
      
      // Procesar la respuesta
      const newIntegration = await response.json();
      console.log("Integración creada:", newIntegration);
      
      // Mostrar mensaje de éxito
      setGlobalAlert({ type: 'success', message: `Integración creada correctamente para el tablero "${selectedBoard?.name || selectedBoardId}"` });
      
      // Limpiar el formulario
      setSelectedBoardId('');
      setDiscordServerId('');
      
      // Actualizar la lista de integraciones
      fetchIntegrations();
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'Error desconocido al crear la integración');
      console.error("Error en handleCreateIntegration:", err);
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteIntegration = async (integrationId: string | undefined) => {
    if (!integrationId || integrationId === 'undefined' || integrationId === 'None' || integrationId.trim() === '') {
      setError('ID de integración no válido o no definido');
      console.error('Intento de eliminar una integración con ID inválido:', integrationId);
      return;
    }
    setPendingDeleteId(integrationId);
    setConfirmOpen(true);
  };

  const confirmDeleteIntegration = async () => {
    if (!pendingDeleteId) return;
    setConfirmOpen(false);
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setError('No hay token de autenticación. Por favor, inicia sesión.');
        return;
      }
      setDeletingId(pendingDeleteId);
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/integration/${pendingDeleteId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.status === 401) {
        setError('Sesión inválida o expirada. Por favor, inicia sesión nuevamente.');
        return;
      }
      if (response.status === 403) {
        setError('No tienes permiso para eliminar esta integración');
        return;
      }
      if (response.status === 404) {
        setError('La integración que intentas eliminar no existe o ya fue eliminada');
        fetchIntegrations();
        return;
      }
      if (!response.ok) {
        setError('Error al eliminar la integración');
        return;
      }
      setGlobalAlert({ type: 'success', message: 'Integración eliminada exitosamente' });
      fetchIntegrations();
    } catch (err) {
      setError('Error desconocido al eliminar la integración');
    } finally {
      setDeletingId(null);
      setPendingDeleteId(undefined);
    }
  };

  const handleOpenUserMappings = (integrationId: string) => {
    navigate(`/integration/${integrationId}/user-mappings`);
  };

  const handleOpenCardMappings = (integrationId: string) => {
    navigate(`/integration/${integrationId}/card-mappings`);
  };

  const handleLoginRedirect = () => {
    navigate('/auth');
  };

  // Buscar detalles adicionales del tablero para mostrarlos en la tabla
  const getBoardName = (boardId: string) => {
    const board = trelloBoards.find(b => b.id === boardId);
    return board ? board.name : boardId;
  };

  return (
    <div className="container mx-auto px-4 py-8">
      {globalAlert && (
        <Alert
          variant={globalAlert.type === 'success' ? 'success' : 'error'}
          title={globalAlert.type === 'success' ? 'Éxito' : 'Error'}
          description={globalAlert.message}
          onClose={() => setGlobalAlert(null)}
          className="mb-4"
        />
      )}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Integraciones</h1>
        <div>
          {!localStorage.getItem('token') && (
            <button
              onClick={handleLoginRedirect}
              className="btn btn-primary"
            >
              Iniciar sesión
            </button>
          )}
        </div>
      </div>
      
      {/* Estado de monitoreo */}
      {localStorage.getItem('token') && (
        <div className={`mb-8 p-4 rounded-lg border ${monitoringStatus.active 
          ? 'bg-green-50 border-green-400' 
          : 'bg-gray-50 border-gray-300'}`}>
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-lg font-semibold">
                {monitoringStatus.active 
                  ? `Monitoreo activo: ${getBoardName(monitoringStatus.monitored_board_id || '')}` 
                  : 'Monitoreo inactivo'}
              </h3>
              <p className="text-sm mt-1 text-gray-600">
                {monitoringStatus.active 
                  ? 'Se están detectando cambios en el tablero y creando canales en Discord automáticamente.' 
                  : 'Inicia el monitoreo en un tablero para detectar cambios automáticamente.'}
              </p>
            </div>
            {monitoringStatus.active && (
              <button
                onClick={handleStopMonitoring}
                disabled={loadingMonitoring}
                className="btn bg-red-600 hover:bg-red-700 text-white"
              >
                {loadingMonitoring ? 'Deteniendo...' : 'Detener monitoreo'}
              </button>
            )}
          </div>
          {monitoringError && (
            <div className="mt-2 text-red-600 text-sm">{monitoringError}</div>
          )}
        </div>
      )}
      
      {/* Mensaje si no hay autenticación */}
      {!localStorage.getItem('token') && (
        <div className="bg-amber-50 border-l-4 border-amber-400 text-amber-700 p-4 rounded-lg mb-8">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-amber-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="font-medium">Atención</p>
              <p className="mt-1">Necesitas iniciar sesión para crear y gestionar integraciones.</p>
              <button 
                onClick={handleLoginRedirect}
                className="mt-2 btn btn-primary text-sm py-1 px-3"
              >
                Iniciar sesión
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Formulario para crear una nueva integración */}
      <div className="card mb-8">
        <h2 className="text-xl font-semibold mb-4">Crear Nueva Integración</h2>
        
        <form onSubmit={handleCreateIntegration}>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="trelloBoardId">
                Tablero de Trello
              </label>
              {loadingBoards ? (
                <div className="flex items-center space-x-2">
                  <svg className="animate-spin h-5 w-5 text-primary-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <p className="text-gray-600">Cargando tableros...</p>
                </div>
              ) : boardsError ? (
                <div className="flex flex-col">
                  <p className="text-red-600 mb-2">{boardsError}</p>
                  <button
                    type="button"
                    onClick={fetchTrelloBoards}
                    className="self-start btn btn-primary text-sm py-1 px-3"
                  >
                    Reintentar
                  </button>
                </div>
              ) : (
                <select
                  id="trelloBoardId"
                  className="form-select w-full"
                  value={selectedBoardId}
                  onChange={(e) => setSelectedBoardId(e.target.value)}
                >
                  <option value="">Selecciona un tablero</option>
                  {trelloBoards.map((board) => (
                    <option key={board.id} value={board.id}>
                      {board.name}
                    </option>
                  ))}
                </select>
              )}
              {selectedBoardId && (
                <p className="mt-1 text-xs text-gray-500">
                  ID: {selectedBoardId}
                </p>
              )}
            </div>
            
            <div>
              <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="discordServerId">
                ID del Servidor de Discord
              </label>
              <input
                id="discordServerId"
                type="text"
                className="form-input w-full"
                placeholder="Ej: 123456789012345678"
                value={discordServerId}
                onChange={(e) => setDiscordServerId(e.target.value)}
              />
              <p className="mt-1 text-xs text-gray-500">
                Debes usar el ID numérico del servidor de Discord
              </p>
            </div>
          </div>
          
          {createError && (
            <div className="bg-red-50 border-l-4 border-red-400 text-red-700 p-4 rounded-lg mb-6">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p>{createError}</p>
                  {createError.includes('Sesión') || createError.includes('autenticación') ? (
                    <button 
                      onClick={handleLoginRedirect}
                      className="mt-2 btn btn-primary text-sm py-1 px-3"
                    >
                      Ir a iniciar sesión
                    </button>
                  ) : null}
                </div>
              </div>
            </div>
          )}
          
          <button
            type="submit"
            disabled={isCreating || !localStorage.getItem('token')}
            className={`${localStorage.getItem('token') 
              ? 'btn btn-primary' 
              : 'btn bg-gray-400 cursor-not-allowed text-white'}`}
          >
            {isCreating ? (
              <span className="flex items-center">
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Creando...
              </span>
            ) : 'Crear Integración'}
          </button>
        </form>
      </div>
      
      {/* Lista de integraciones */}
      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Integraciones Existentes</h2>
        
        {!localStorage.getItem('token') ? (
          <div className="text-gray-600">
            <p>Inicia sesión para ver tus integraciones.</p>
            <button 
              onClick={handleLoginRedirect}
              className="mt-4 btn btn-primary"
            >
              Iniciar sesión
            </button>
          </div>
        ) : loading ? (
          <div className="flex justify-center items-center py-8">
            <svg className="animate-spin h-8 w-8 text-primary-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
          </div>
        ) : error ? (
          <div className="bg-red-50 border-l-4 border-red-400 text-red-700 p-4 rounded-lg">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p>{error}</p>
                {error.includes('Sesión') && (
                  <button 
                    onClick={handleLoginRedirect}
                    className="mt-2 btn btn-primary text-sm py-1 px-3"
                  >
                    Ir a iniciar sesión
                  </button>
                )}
              </div>
            </div>
          </div>
        ) : integrations.length === 0 ? (
          <div className="text-center py-8">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"></path>
            </svg>
            <p className="mt-2 text-gray-600">No tienes integraciones configuradas.</p>
            <p className="text-sm text-gray-500 mt-1">Crea una nueva integración usando el formulario de arriba.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full bg-white rounded-lg overflow-hidden">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="py-3 px-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Tablero Trello
                  </th>
                  <th className="py-3 px-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Servidor Discord
                  </th>
                  <th className="py-3 px-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Fecha de Creación
                  </th>
                  <th className="py-3 px-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Estado
                  </th>
                  <th className="py-3 px-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Monitoreo
                  </th>
                  <th className="py-3 px-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                    Acciones
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {integrations.map((integration) => (
                  <tr key={integration._id} className="hover:bg-gray-50 transition-colors duration-150">
                    <td className="py-4 px-4">
                      <div className="text-sm font-medium text-gray-900">{getBoardName(integration.trello_board_id)}</div>
                      <div className="text-xs text-gray-500">ID: {integration.trello_board_id}</div>
                    </td>
                    <td className="py-4 px-4">
                      <div className="text-sm text-gray-900">{integration.discord_server_id}</div>
                    </td>
                    <td className="py-4 px-4">
                      <div className="text-sm text-gray-900">{new Date(integration.created_at).toLocaleDateString()}</div>
                    </td>
                    <td className="py-4 px-4">
                      <span className={`badge ${integration.active ? 'badge-success' : 'badge-error'}`}>
                        {integration.active ? 'Activa' : 'Inactiva'}
                      </span>
                    </td>
                    <td className="py-4 px-4">
                      {monitoringStatus.active && monitoringStatus.monitored_board_id === integration.trello_board_id ? (
                        <span className="badge badge-success flex items-center">
                          <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                          </svg>
                          Activo
                        </span>
                      ) : (
                        <button
                          onClick={() => handleStartMonitoring(integration.trello_board_id)}
                          disabled={monitoringStatus.active || loadingMonitoring}
                          className={`btn btn-sm ${
                            monitoringStatus.active 
                              ? 'bg-gray-300 cursor-not-allowed' 
                              : 'bg-green-600 hover:bg-green-700 text-white'
                          }`}
                        >
                          {loadingMonitoring ? 'Iniciando...' : 'Iniciar monitoreo'}
                        </button>
                      )}
                    </td>
                    <td className="py-4 px-4 text-sm space-y-2">
                      <button
                        onClick={() => handleOpenUserMappings(integration._id)}
                        className="flex items-center text-indigo-600 hover:text-indigo-900 mr-2"
                      >
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                        </svg>
                        Mapeos de Usuarios
                      </button>
                      <button
                        onClick={() => handleOpenCardMappings(integration._id)}
                        className="flex items-center text-green-600 hover:text-green-900 mr-2"
                      >
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path>
                        </svg>
                        Mapeos de Listas
                      </button>
                      <button
                        onClick={() => handleDeleteIntegration(integration._id)}
                        disabled={deletingId === integration._id}
                        className={`flex items-center ${
                          deletingId === integration._id 
                            ? 'text-gray-400 cursor-not-allowed' 
                            : 'text-red-600 hover:text-red-900'
                        }`}
                      >
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                        </svg>
                        {deletingId === integration._id ? 'Eliminando...' : 'Eliminar'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      <ConfirmDialog
        open={confirmOpen}
        title="¿Eliminar integración?"
        description="¿Estás seguro de que deseas eliminar esta integración? Esta acción no se puede deshacer."
        confirmText="Eliminar"
        cancelText="Cancelar"
        variant="danger"
        onConfirm={confirmDeleteIntegration}
        onCancel={() => { setConfirmOpen(false); setPendingDeleteId(undefined); }}
      />
    </div>
  );
};

export default IntegrationsPage; 