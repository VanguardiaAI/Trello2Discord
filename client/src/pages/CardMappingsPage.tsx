import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ConfirmDialog } from '../components/ui/confirm-dialog';

interface TrelloCard {
  id: string;
  name: string;
  url: string;
  members: string[];
}

interface DiscordChannel {
  id: string;
  name: string;
}

interface CardChannelMapping {
  _id: string;
  trello_card_id: string;
  trello_card_name: string;
  discord_channel_id: string;
  discord_channel_name: string;
  integration_id: string;
  created_at: string;
  created_automatically: boolean;
}

const CardMappingsPage = () => {
  const { integrationId } = useParams<{ integrationId: string }>();
  const navigate = useNavigate();
  
  const [trelloCards, setTrelloCards] = useState<TrelloCard[]>([]);
  const [discordChannels, setDiscordChannels] = useState<DiscordChannel[]>([]);
  const [mappings, setMappings] = useState<CardChannelMapping[]>([]);
  
  const [selectedTrelloCard, setSelectedTrelloCard] = useState('');
  const [selectedDiscordChannel, setSelectedDiscordChannel] = useState('');
  
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
    
    // Primero obtener los detalles de la integración para conocer el ID del tablero
    fetchIntegrationDetails();
  }, [integrationId, navigate]);
  
  const fetchIntegrationDetails = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      if (!token || !integrationId) {
        throw new Error('Falta token o ID de integración');
      }
      
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/integration/${integrationId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Error al obtener detalles de la integración');
      }
      
      const data = await response.json();
      if (data.integration && data.integration.trello_board_id) {
        // Una vez que tenemos el ID del tablero, podemos obtener las tarjetas y otros datos
        await Promise.all([
          fetchTrelloCardsDirectly(data.integration.trello_board_id),
          fetchDiscordChannels(),
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
  
  const fetchTrelloCardsDirectly = async (boardId: string) => {
    try {
      // Usar el mismo endpoint que funciona en DebugPage.tsx
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/debug/trello/board/${boardId}/cards`);
      
      if (!response.ok) {
        throw new Error('Error al obtener tarjetas del tablero de Trello');
      }
      
      const data = await response.json();
      
      if (data.status === 'success' && data.cards) {
        // Transformar las tarjetas al formato esperado por el componente
        const formattedCards: TrelloCard[] = data.cards.map((card: any) => ({
          id: card.id,
          name: card.name,
          url: card.url,
          members: card.members || []
        }));
        
        setTrelloCards(formattedCards);
      } else {
        throw new Error(data.message || 'No se pudieron obtener las tarjetas del tablero');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    }
  };
  
  const fetchDiscordChannels = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/card-channel/integration/${integrationId}/channels`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Error al obtener canales de Discord');
      }
      
      const data = await response.json();
      setDiscordChannels(data.discord_channels || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido');
    }
  };
  
  const fetchMappings = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/card-channel/integration/${integrationId}/mapping`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error('Error al obtener mapeos de tarjetas-canales');
      }
      
      const data = await response.json();
      
      // Filtrar para eliminar posibles mapeos con IDs inválidos
      const validMappings = (data.mappings || []).filter((mapping: any) => {
        const hasValidId = mapping._id && 
                          mapping._id !== 'None' && 
                          mapping._id !== 'undefined' && 
                          mapping._id !== 'null' && 
                          mapping._id.trim() !== '';
        
        if (!hasValidId) {
          console.warn('Se encontró un mapeo con ID inválido:', mapping);
        }
        
        return hasValidId;
      });
      
      if (validMappings.length !== (data.mappings || []).length) {
        console.warn(`Se filtraron ${(data.mappings || []).length - validMappings.length} mapeos con IDs inválidos`);
      }
      
      setMappings(validMappings);
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
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/card-channel/mapping/${pendingDeleteId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Error desconocido del servidor' }));
        throw new Error(errorData.message || `Error al eliminar el mapeo: ${response.status} ${response.statusText}`);
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
  
  // Filtrar tarjetas y canales que ya están mapeados
  const unmappedTrelloCards = trelloCards.filter(
    card => !mappings.some(mapping => mapping.trello_card_id === card.id)
  );
  
  const unmappedDiscordChannels = discordChannels.filter(
    channel => !mappings.some(mapping => mapping.discord_channel_id === channel.id)
  );
  
  // Función para crear mapeo de tarjeta-canal directamente
  const handleCreateMappingDirectly = async () => {
    if (!selectedTrelloCard || !selectedDiscordChannel) {
      setError('Debes seleccionar una tarjeta de Trello y un canal de Discord');
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
      
      // Obtener información de la tarjeta de Trello seleccionada
      const trelloCard = trelloCards.find(card => card.id === selectedTrelloCard);
      if (!trelloCard) {
        throw new Error('Tarjeta de Trello seleccionada no encontrada');
      }
      
      // Obtener información del canal de Discord seleccionado
      const discordChannel = discordChannels.find(channel => channel.id === selectedDiscordChannel);
      if (!discordChannel) {
        throw new Error('Canal de Discord seleccionado no encontrado');
      }
      
      // Crear objeto de mapeo directamente
      const mappingData = {
        trello_card_id: trelloCard.id,
        trello_card_name: trelloCard.name,
        discord_channel_id: discordChannel.id,
        discord_channel_name: discordChannel.name,
        integration_id: integrationId,
        created_automatically: false
      };
      
      console.log('Creando mapeo directo:', mappingData);
      
      // Intentar crear el mapeo directamente en la base de datos
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/card-channel/create-direct`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(mappingData)
      });
      
      // Capturar el texto de respuesta para diagnóstico
      const responseText = await response.text();
      let responseData;
      
      try {
        // Intentar analizar como JSON
        responseData = JSON.parse(responseText);
      } catch (e) {
        // Si no es JSON, usar el texto como mensaje
        responseData = { message: responseText || 'Error desconocido en el servidor' };
      }
      
      if (!response.ok) {
        console.error('Error en la respuesta:', response.status, responseText);
        
        if (response.status === 404) {
          throw new Error('La ruta para crear mapeos directamente no está implementada en el servidor');
        }
        
        throw new Error(responseData.error || responseData.message || `Error del servidor: ${response.status} ${response.statusText}`);
      }
      
      // Comprobar si hay advertencias pero la operación fue exitosa
      if (responseData.warning) {
        // Esto significa que ya existe un mapeo, pero no es necesariamente un error fatal
        setSuccess(`${responseData.warning} (ID: ${responseData.mapping_id})`);
        
        // Actualizar la lista de mapeos
        fetchMappings();
        
        // Limpiar el formulario
        setSelectedTrelloCard('');
        setSelectedDiscordChannel('');
        
        // Limpiar mensaje de éxito después de 3 segundos
        setTimeout(() => {
          setSuccess(null);
        }, 3000);
        
        setIsCreating(false);
        return;
      }
      
      // Limpiar el formulario
      setSelectedTrelloCard('');
      setSelectedDiscordChannel('');
      
      // Mostrar mensaje de éxito
      setSuccess(responseData.message || 'Mapeo de tarjeta-canal creado exitosamente');
      
      // Actualizar la lista de mapeos
      fetchMappings();
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
        <h1 className="text-3xl font-bold text-gray-900">Mapeos de Tarjetas y Canales</h1>
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
            <h2 className="text-xl font-semibold mb-4">Crear Nuevo Mapeo Manual</h2>
            
            <form onSubmit={(e) => {
              e.preventDefault();
              handleCreateMappingDirectly();
            }}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <div>
                  <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="trelloCard">
                    Tarjeta de Trello
                  </label>
                  {unmappedTrelloCards.length === 0 ? (
                    <p className="text-yellow-600">No hay tarjetas disponibles para mapear.</p>
                  ) : (
                    <select
                      id="trelloCard"
                      className="form-select w-full"
                      value={selectedTrelloCard}
                      onChange={(e) => setSelectedTrelloCard(e.target.value)}
                    >
                      <option value="">Selecciona una tarjeta</option>
                      {unmappedTrelloCards.map((card) => (
                        <option key={card.id} value={card.id}>
                          {card.name}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
                
                <div>
                  <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="discordChannel">
                    Canal de Discord
                  </label>
                  {unmappedDiscordChannels.length === 0 ? (
                    <p className="text-yellow-600">No hay canales disponibles para mapear.</p>
                  ) : (
                    <select
                      id="discordChannel"
                      className="form-select w-full"
                      value={selectedDiscordChannel}
                      onChange={(e) => setSelectedDiscordChannel(e.target.value)}
                    >
                      <option value="">Selecciona un canal</option>
                      {unmappedDiscordChannels.map((channel) => (
                        <option key={channel.id} value={channel.id}>
                          #{channel.name}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              </div>
              
              <button
                type="submit"
                disabled={isCreating || unmappedTrelloCards.length === 0 || unmappedDiscordChannels.length === 0}
                className={`${
                  isCreating || unmappedTrelloCards.length === 0 || unmappedDiscordChannels.length === 0
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
              
              {(unmappedTrelloCards.length === 0 || unmappedDiscordChannels.length === 0) && (
                <p className="text-yellow-600 mt-2 text-sm">
                  {unmappedTrelloCards.length === 0 && unmappedDiscordChannels.length === 0
                    ? 'No hay tarjetas ni canales disponibles para mapear.'
                    : unmappedTrelloCards.length === 0
                    ? 'No hay tarjetas de Trello disponibles para mapear.'
                    : 'No hay canales de Discord disponibles para mapear.'}
                </p>
              )}
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
                <p className="mt-2 text-gray-600">No hay mapeos de tarjetas-canales configurados.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full bg-white rounded-lg overflow-hidden">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="py-3 px-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                        Tarjeta de Trello
                      </th>
                      <th className="py-3 px-4 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
                        Canal de Discord
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
                          <div className="text-sm font-medium text-gray-900">{mapping.trello_card_name}</div>
                        </td>
                        <td className="py-4 px-4">
                          <div className="text-sm text-gray-900">#{mapping.discord_channel_name}</div>
                        </td>
                        <td className="py-4 px-4">
                          <div className="text-sm text-gray-900">{new Date(mapping.created_at).toLocaleDateString()}</div>
                        </td>
                        <td className="py-4 px-4">
                          <span className={`badge ${mapping.created_automatically ? 'badge-info' : 'badge-success'}`}>
                            {mapping.created_automatically ? 'Automático' : 'Manual'}
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

export default CardMappingsPage; 