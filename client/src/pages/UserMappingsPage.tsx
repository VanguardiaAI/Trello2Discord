import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ConfirmDialog } from '../components/ui/confirm-dialog';

interface TrelloUser {
  id: string;
  username: string;
  full_name: string;
}

interface DiscordUser {
  id: string;
  username: string;
  display_name: string;
}

interface UserMapping {
  _id: string;
  trello_user_id: string;
  trello_username: string;
  discord_user_id: string;
  discord_username: string;
  integration_id: string;
  created_at: string;
}

const UserMappingsPage = () => {
  const { integrationId } = useParams<{ integrationId: string }>();
  const navigate = useNavigate();
  
  const [trelloUsers, setTrelloUsers] = useState<TrelloUser[]>([]);
  const [discordUsers, setDiscordUsers] = useState<DiscordUser[]>([]);
  const [mappings, setMappings] = useState<UserMapping[]>([]);
  
  const [selectedTrelloUser, setSelectedTrelloUser] = useState('');
  const [selectedDiscordUser, setSelectedDiscordUser] = useState('');
  
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  const [loading, setLoading] = useState<boolean>(true);
  
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  
  useEffect(() => {
    // Verificar autenticación
    const token = localStorage.getItem('token');
    if (!token) {
      navigate('/auth');
      return;
    }
    
    // Primero obtener los detalles de la integración para conocer el ID del tablero de Trello
    fetchIntegrationDetails();
  }, [integrationId, navigate]);
  
  const fetchIntegrationDetails = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      if (!token || !integrationId) {
        throw new Error('Falta token o ID de integración');
      }
      
      const response = await fetch(`http://localhost:5000/api/integration/${integrationId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Error al obtener detalles de la integración');
      }
      
      const data = await response.json();
      if (data.integration && data.integration.trello_board_id) {
        // Una vez que tenemos el ID del tablero, podemos obtener los usuarios y otros datos
        await Promise.all([
          fetchTrelloUsers(data.integration.trello_board_id),
          fetchDiscordUsers(),
          fetchMappings()
        ]);
      } else {
        throw new Error('Integración no válida o sin tablero de Trello asociado');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    } finally {
      setLoading(false);
    }
  };
  
  const fetchTrelloUsers = async (boardId: string) => {
    try {
      // Usar la misma ruta que funciona en DebugPage.tsx
      const response = await fetch(`http://localhost:5000/api/debug/trello/board/${boardId}/details`);
      
      if (!response.ok) {
        throw new Error('Error al obtener detalles del tablero de Trello');
      }
      
      const data = await response.json();
      
      if (data.status === 'success' && data.members) {
        // Transformar los miembros al formato esperado por el componente
        const formattedUsers: TrelloUser[] = data.members.map((member: any) => ({
          id: member.id,
          username: member.username,
          full_name: member.full_name
        }));
        
        setTrelloUsers(formattedUsers);
      } else {
        throw new Error(data.message || 'No se pudieron obtener los miembros del tablero');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    }
  };
  
  const fetchDiscordUsers = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://localhost:5000/api/user-mapping/integration/${integrationId}/users/discord`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Error al obtener usuarios de Discord');
      }
      
      const data = await response.json();
      setDiscordUsers(data.discord_users || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    }
  };
  
  const fetchMappings = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://localhost:5000/api/user-mapping/integration/${integrationId}/mapping`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Error al obtener mapeos de usuarios');
      }
      
      const data = await response.json();
      setMappings(data.mappings || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    }
  };
  
  const handleDeleteMapping = async (mappingId: string) => {
    if (!mappingId || mappingId === 'undefined' || mappingId === 'null' || mappingId === 'None' || mappingId.trim() === '') {
      setError('El ID del mapeo no es válido. Por favor, actualice la página e intente de nuevo.');
      console.error('Intento de eliminar un mapeo con ID inválido:', mappingId);
      return;
    }
    setPendingDeleteId(mappingId);
    setConfirmOpen(true);
  };
  
  const confirmDeleteMapping = async () => {
    if (!pendingDeleteId) return;
    setConfirmOpen(false);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://localhost:5000/api/user-mapping/mapping/${pendingDeleteId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!response.ok) {
        throw new Error('Error al eliminar el mapeo');
      }
      setSuccess('Mapeo eliminado exitosamente');
      fetchMappings();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido al eliminar el mapeo');
    } finally {
      setPendingDeleteId(null);
    }
  };
  
  // Agregar función para crear mapeo de usuario directamente
  const handleCreateMappingDirectly = async () => {
    if (!selectedTrelloUser || !selectedDiscordUser) {
      setError('Debes seleccionar un usuario de Trello y un usuario de Discord');
      return;
    }
    
    try {
      setIsCreating(true);
      setError(null);
      
      const token = localStorage.getItem('token');
      if (!token) {
        setError('No hay token de autenticación. Por favor, inicia sesión.');
        setIsCreating(false);
        return;
      }
      
      // Obtener información del usuario de Trello seleccionado
      const trelloUser = trelloUsers.find(u => u.id === selectedTrelloUser);
      if (!trelloUser) {
        throw new Error('Usuario de Trello seleccionado no encontrado');
      }
      
      // Obtener información del usuario de Discord seleccionado
      const discordUser = discordUsers.find(u => u.id === selectedDiscordUser);
      if (!discordUser) {
        throw new Error('Usuario de Discord seleccionado no encontrado');
      }
      
      // Crear objeto de mapeo directamente
      const mappingData = {
        trello_user_id: trelloUser.id,
        trello_username: trelloUser.username,
        discord_user_id: discordUser.id,
        discord_username: discordUser.username || discordUser.display_name,
        integration_id: integrationId
      };
      
      console.log('Creando mapeo directo:', mappingData);
      
      // Intentar crear el mapeo directamente en la base de datos
      const response = await fetch(`http://localhost:5000/api/user-mapping/create-direct`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(mappingData)
      });
      
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('La ruta para crear mapeos directamente no está implementada en el servidor');
        }
        
        const errorData = await response.json().catch(() => ({ message: 'Error desconocido en el servidor' }));
        throw new Error(errorData.message || 'Error al crear el mapeo');
      }
      
      const responseData = await response.json();
      
      // Limpiar el formulario
      setSelectedTrelloUser('');
      setSelectedDiscordUser('');
      
      // Mostrar mensaje de éxito
      setSuccess(responseData.message || 'Mapeo de usuario creado exitosamente');
      
      // Actualizar la lista de mapeos
      fetchMappings();
      
      // Limpiar mensaje de éxito después de 3 segundos
      setTimeout(() => {
        setSuccess(null);
      }, 3000);
    } catch (err) {
      console.error('Error al crear mapeo directo:', err);
      setError(err instanceof Error ? err.message : 'Error desconocido al crear el mapeo directo');
    } finally {
      setIsCreating(false);
    }
  };
  
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Mapeos de Miembros</h1>
        <button 
          onClick={() => navigate('/')}
          className="btn btn-secondary"
        >
          Volver a Integraciones
        </button>
      </div>
      
      {error && (
        <div className="bg-red-50 border-l-4 border-red-400 text-red-700 p-4 rounded-lg mb-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p>{error}</p>
              <button 
                onClick={fetchIntegrationDetails}
                className="mt-2 btn btn-primary text-sm py-1 px-3"
              >
                Reintentar
              </button>
            </div>
          </div>
        </div>
      )}
      
      {success && (
        <div className="bg-green-50 border-l-4 border-green-400 text-green-700 p-4 rounded-lg mb-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              {success}
            </div>
          </div>
        </div>
      )}
      
      {loading ? (
        <div className="card flex justify-center items-center py-8">
          <svg className="animate-spin h-8 w-8 text-primary-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          <p className="text-gray-600 ml-3">Cargando datos, por favor espere...</p>
        </div>
      ) : (
        <>
          {/* Formulario para crear un nuevo mapeo */}
          <div className="card mb-8">
            <h2 className="text-xl font-semibold mb-4">Crear Nuevo Mapeo de Miembros Manual</h2>
            
            <form onSubmit={(e) => {
              e.preventDefault();
              handleCreateMappingDirectly();
            }}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div>
                  <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="trelloMember">
                    Miembro de Trello
                  </label>
                  {trelloUsers.length === 0 ? (
                    <p className="text-yellow-600">No hay miembros disponibles para mapear.</p>
                  ) : (
                    <select
                      id="trelloMember"
                      className="form-select w-full"
                      value={selectedTrelloUser}
                      onChange={(e) => setSelectedTrelloUser(e.target.value)}
                    >
                      <option value="">Selecciona un miembro</option>
                      {trelloUsers.map((user) => (
                        <option key={user.id} value={user.id}>
                          {user.full_name} ({user.username})
                        </option>
                      ))}
                    </select>
                  )}
                </div>
                
                <div>
                  <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="discordUser">
                    Usuario de Discord
                  </label>
                  {discordUsers.length === 0 ? (
                    <p className="text-yellow-600">No hay usuarios disponibles para mapear.</p>
                  ) : (
                    <select
                      id="discordUser"
                      className="form-select w-full"
                      value={selectedDiscordUser}
                      onChange={(e) => setSelectedDiscordUser(e.target.value)}
                    >
                      <option value="">Selecciona un usuario</option>
                      {discordUsers.map((user) => (
                        <option key={user.id} value={user.id}>
                          {user.display_name || user.username}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              </div>
              
              <button
                type="submit"
                disabled={isCreating || trelloUsers.length === 0 || discordUsers.length === 0}
                className={`${
                  isCreating || trelloUsers.length === 0 || discordUsers.length === 0
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'btn btn-primary'
                } text-white font-medium py-2 px-4 rounded`}
              >
                {isCreating ? (
                  <span className="flex items-center">
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Creando...
                  </span>
                ) : 'Crear Mapeo'}
              </button>
            </form>
          </div>
          
          {/* Lista de mapeos */}
          <div className="card">
            <h2 className="text-xl font-semibold mb-4">Mapeos Existentes</h2>
            
            {mappings.length === 0 ? (
              <div className="text-center py-8">
                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path>
                </svg>
                <p className="mt-2 text-gray-600">No hay mapeos de usuarios configurados.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full bg-white rounded-lg overflow-hidden">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="py-3 px-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                        Miembro de Trello
                      </th>
                      <th className="py-3 px-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                        Usuario de Discord
                      </th>
                      <th className="py-3 px-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                        Creado
                      </th>
                      <th className="py-3 px-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                        Tipo
                      </th>
                      <th className="py-3 px-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                        Acciones
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {mappings.map((mapping) => (
                      <tr key={mapping._id} className="hover:bg-gray-50 transition-colors duration-150">
                        <td className="py-4 px-4">
                          <div className="text-sm font-medium text-gray-900">{mapping.trello_username}</div>
                        </td>
                        <td className="py-4 px-4">
                          <div className="text-sm font-medium text-gray-900">{mapping.discord_username}</div>
                        </td>
                        <td className="py-4 px-4">
                          <div className="text-sm text-gray-900">{new Date(mapping.created_at).toLocaleDateString()}</div>
                        </td>
                        <td className="py-4 px-4">
                          <span className="badge badge-success">
                            Manual
                          </span>
                        </td>
                        <td className="py-4 px-4 text-sm">
                          <button
                            onClick={() => handleDeleteMapping(mapping._id)}
                            className="flex items-center text-red-600 hover:text-red-900"
                          >
                            <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                            </svg>
                            Eliminar
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
            title="¿Eliminar mapeo?"
            description="¿Estás seguro de que deseas eliminar este mapeo? Esta acción no se puede deshacer."
            confirmText="Eliminar"
            cancelText="Cancelar"
            variant="danger"
            onConfirm={confirmDeleteMapping}
            onCancel={() => { setConfirmOpen(false); setPendingDeleteId(null); }}
          />
        </>
      )}
    </div>
  );
};

export default UserMappingsPage; 