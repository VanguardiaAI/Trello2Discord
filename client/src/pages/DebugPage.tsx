import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

interface TrelloBoard {
  id: string;
  name: string;
  url: string;
  closed: boolean;
  description: string;
}

interface BoardList {
  id: string;
  name: string;
  closed: boolean;
}

interface BoardMember {
  id: string;
  username: string;
  full_name: string;
}

interface CardLabel {
  id: string;
  name: string;
  color: string;
}

interface BoardCard {
  id: string;
  name: string;
  description: string;
  url: string;
  short_url: string;
  closed: boolean;
  id_list: string;
  id_board: string;
  due: string | null;
  labels: CardLabel[];
}

interface BoardDetails {
  id: string;
  name: string;
  url: string;
  description: string;
  lists: BoardList[];
  members: BoardMember[];
}

const DebugPage = () => {
  const navigate = useNavigate();
  const [credentialsStatus, setCredentialsStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [credentialsMessage, setCredentialsMessage] = useState('Verificando credenciales...');
  
  const [boards, setBoards] = useState<TrelloBoard[]>([]);
  const [boardsLoading, setBoardsLoading] = useState(false);
  const [boardsError, setBoardsError] = useState<string | null>(null);
  
  const [selectedBoardId, setSelectedBoardId] = useState('');
  const [boardDetails, setBoardDetails] = useState<BoardDetails | null>(null);
  const [boardDetailsLoading, setBoardDetailsLoading] = useState(false);
  const [boardDetailsError, setBoardDetailsError] = useState<string | null>(null);
  
  const [boardCards, setBoardCards] = useState<BoardCard[]>([]);
  const [boardCardsLoading, setBoardCardsLoading] = useState(false);
  const [boardCardsError, setBoardCardsError] = useState<string | null>(null);

  // Verificar credenciales al cargar
  useEffect(() => {
    checkCredentials();
  }, []);

  const checkCredentials = async () => {
    try {
      setCredentialsStatus('loading');
      setCredentialsMessage('Verificando credenciales...');
      
      const response = await fetch('http://localhost:5000/api/debug/trello/check-credentials-detailed');
      const data = await response.json();
      
      if (data.status === 'success') {
        setCredentialsStatus('success');
        setCredentialsMessage(`${data.message}. Usuario: ${data.user_info.fullName} (${data.user_info.username})`);
        // Cargar tableros automáticamente si las credenciales son válidas
        fetchBoards();
      } else {
        setCredentialsStatus('error');
        setCredentialsMessage(data.message);
        console.error('Error de credenciales:', data);
      }
    } catch (err) {
      setCredentialsStatus('error');
      setCredentialsMessage(err instanceof Error ? err.message : 'Error al verificar credenciales');
      console.error('Error al verificar credenciales:', err);
    }
  };

  const fetchBoards = async () => {
    try {
      setBoardsLoading(true);
      setBoardsError(null);
      
      const response = await fetch('http://localhost:5000/api/debug/trello/boards');
      const data = await response.json();
      
      if (data.status === 'success') {
        setBoards(data.boards);
      } else {
        setBoardsError(data.message);
      }
    } catch (err) {
      setBoardsError(err instanceof Error ? err.message : 'Error al obtener tableros');
    } finally {
      setBoardsLoading(false);
    }
  };

  const fetchBoardDetails = async (boardId: string) => {
    if (!boardId) return;
    
    try {
      setBoardDetailsLoading(true);
      setBoardDetailsError(null);
      
      const response = await fetch(`http://localhost:5000/api/debug/trello/board/${boardId}/details`);
      const data = await response.json();
      
      if (data.status === 'success') {
        setBoardDetails({
          ...data.board,
          lists: data.lists,
          members: data.members
        });
        
        // Cargar tarjetas del tablero
        fetchBoardCards(boardId);
      } else {
        setBoardDetailsError(data.message);
      }
    } catch (err) {
      setBoardDetailsError(err instanceof Error ? err.message : 'Error al obtener detalles del tablero');
    } finally {
      setBoardDetailsLoading(false);
    }
  };
  
  const fetchBoardCards = async (boardId: string) => {
    if (!boardId) return;
    
    try {
      setBoardCardsLoading(true);
      setBoardCardsError(null);
      
      const response = await fetch(`http://localhost:5000/api/debug/trello/board/${boardId}/cards`);
      const data = await response.json();
      
      if (data.status === 'success') {
        setBoardCards(data.cards);
      } else {
        setBoardCardsError(data.message);
      }
    } catch (err) {
      setBoardCardsError(err instanceof Error ? err.message : 'Error al obtener tarjetas del tablero');
    } finally {
      setBoardCardsLoading(false);
    }
  };

  const handleBoardSelect = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const boardId = e.target.value;
    setSelectedBoardId(boardId);
    
    if (boardId) {
      fetchBoardDetails(boardId);
    } else {
      setBoardDetails(null);
      setBoardCards([]);
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Depuración de Trello</h1>
        <button 
          onClick={() => navigate('/')}
          className="bg-gray-500 hover:bg-gray-600 text-white font-medium py-2 px-4 rounded"
        >
          Volver a Integraciones
        </button>
      </div>
      
      {/* Estado de las credenciales */}
      <div className={`p-4 mb-6 rounded ${
        credentialsStatus === 'loading' ? 'bg-gray-100' : 
        credentialsStatus === 'success' ? 'bg-green-100' : 'bg-red-100'
      }`}>
        <h2 className="text-xl font-semibold mb-2">Estado de las Credenciales de Trello</h2>
        <p>{credentialsMessage}</p>
        {credentialsStatus === 'error' && (
          <button 
            onClick={checkCredentials}
            className="mt-2 bg-blue-500 hover:bg-blue-600 text-white font-medium py-1 px-3 text-sm rounded"
          >
            Reintentar
          </button>
        )}
      </div>
      
      {/* Lista de tableros */}
      <div className="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Tableros de Trello</h2>
        
        {boardsLoading ? (
          <p>Cargando tableros...</p>
        ) : boardsError ? (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            <p>{boardsError}</p>
            <button 
              onClick={fetchBoards}
              className="mt-2 bg-blue-500 hover:bg-blue-600 text-white font-medium py-1 px-3 text-sm rounded"
            >
              Reintentar
            </button>
          </div>
        ) : boards.length === 0 ? (
          <p>No se encontraron tableros. Asegúrate de que tu cuenta de Trello tiene tableros creados.</p>
        ) : (
          <div>
            <select
              className="shadow border rounded w-full py-2 px-3 text-gray-700 mb-4"
              value={selectedBoardId}
              onChange={handleBoardSelect}
            >
              <option value="">Selecciona un tablero</option>
              {boards.map(board => (
                <option key={board.id} value={board.id}>
                  {board.name}
                </option>
              ))}
            </select>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {boards.map(board => (
                <div 
                  key={board.id} 
                  className={`border p-4 rounded ${selectedBoardId === board.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200'}`}
                  onClick={() => {
                    setSelectedBoardId(board.id);
                    fetchBoardDetails(board.id);
                  }}
                >
                  <h3 className="font-semibold">{board.name}</h3>
                  <p className="text-sm text-gray-600 truncate">{board.description || 'Sin descripción'}</p>
                  <p className="text-xs text-gray-500 mt-2">ID: {board.id}</p>
                  {board.closed && <span className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded mt-2 inline-block">Cerrado</span>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
      
      {/* Detalles del tablero seleccionado */}
      {selectedBoardId && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4">Detalles del Tablero</h2>
          
          {boardDetailsLoading ? (
            <p>Cargando detalles...</p>
          ) : boardDetailsError ? (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
              <p>{boardDetailsError}</p>
              <button 
                onClick={() => fetchBoardDetails(selectedBoardId)}
                className="mt-2 bg-blue-500 hover:bg-blue-600 text-white font-medium py-1 px-3 text-sm rounded"
              >
                Reintentar
              </button>
            </div>
          ) : boardDetails ? (
            <div>
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-2">Información del Tablero</h3>
                <p><strong>Nombre:</strong> {boardDetails.name}</p>
                <p><strong>Descripción:</strong> {boardDetails.description || 'Sin descripción'}</p>
                <p><strong>URL:</strong> <a href={boardDetails.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{boardDetails.url}</a></p>
                <p><strong>ID:</strong> {boardDetails.id}</p>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h3 className="text-lg font-semibold mb-2">Listas ({boardDetails.lists.length})</h3>
                  {boardDetails.lists.length === 0 ? (
                    <p>Este tablero no tiene listas.</p>
                  ) : (
                    <ul className="border rounded divide-y">
                      {boardDetails.lists.map(list => (
                        <li key={list.id} className="p-3">
                          <div className="flex justify-between items-center">
                            <span>{list.name}</span>
                            {list.closed && <span className="text-xs bg-red-100 text-red-800 px-2 py-1 rounded">Cerrada</span>}
                          </div>
                          <span className="text-xs text-gray-500">ID: {list.id}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                
                <div>
                  <h3 className="text-lg font-semibold mb-2">Miembros ({boardDetails.members.length})</h3>
                  {boardDetails.members.length === 0 ? (
                    <p>Este tablero no tiene miembros.</p>
                  ) : (
                    <ul className="border rounded divide-y">
                      {boardDetails.members.map(member => (
                        <li key={member.id} className="p-3">
                          <div className="font-medium">{member.full_name}</div>
                          <div className="text-sm text-gray-600">@{member.username}</div>
                          <span className="text-xs text-gray-500">ID: {member.id}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <p>Selecciona un tablero para ver sus detalles.</p>
          )}
          
          {/* Tarjetas del tablero */}
          <div className="mt-8">
            <h2 className="text-xl font-semibold mb-4">Tarjetas del Tablero</h2>
            
            {boardCardsLoading ? (
              <p>Cargando tarjetas...</p>
            ) : boardCardsError ? (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
                <p>{boardCardsError}</p>
                <button 
                  onClick={() => fetchBoardCards(selectedBoardId)}
                  className="mt-2 bg-blue-500 hover:bg-blue-600 text-white font-medium py-1 px-3 text-sm rounded"
                >
                  Reintentar
                </button>
              </div>
            ) : boardCards.length === 0 ? (
              <p>No se encontraron tarjetas en este tablero.</p>
            ) : (
              <div className="overflow-auto max-h-96">
                <table className="min-w-full border-collapse">
                  <thead>
                    <tr className="bg-gray-200">
                      <th className="px-4 py-2 text-left border">Nombre</th>
                      <th className="px-4 py-2 text-left border">Lista</th>
                      <th className="px-4 py-2 text-left border">Etiquetas</th>
                      <th className="px-4 py-2 text-left border">Vencimiento</th>
                      <th className="px-4 py-2 text-left border">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {boardCards.map(card => {
                      // Encontrar el nombre de la lista
                      const list = boardDetails?.lists.find(l => l.id === card.id_list);
                      
                      return (
                        <tr key={card.id} className="hover:bg-gray-50">
                          <td className="px-4 py-2 border">
                            <p className="font-medium">{card.name}</p>
                            <p className="text-xs text-gray-500">ID: {card.id}</p>
                          </td>
                          <td className="px-4 py-2 border">{list?.name || 'Lista desconocida'}</td>
                          <td className="px-4 py-2 border">
                            {card.labels.length === 0 ? (
                              <span className="text-gray-400">Sin etiquetas</span>
                            ) : (
                              <div className="flex flex-wrap gap-1">
                                {card.labels.map(label => (
                                  <span 
                                    key={label.id} 
                                    className="px-2 py-1 text-xs rounded"
                                    style={{ 
                                      backgroundColor: label.color ? `#${label.color}20` : '#f0f0f0',
                                      color: label.color ? `#${label.color}` : '#666',
                                      border: `1px solid ${label.color ? `#${label.color}` : '#ddd'}`
                                    }}
                                  >
                                    {label.name || label.color}
                                  </span>
                                ))}
                              </div>
                            )}
                          </td>
                          <td className="px-4 py-2 border">
                            {card.due ? new Date(card.due).toLocaleDateString() : 'Sin fecha'}
                          </td>
                          <td className="px-4 py-2 border">
                            <a 
                              href={card.url} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="text-blue-500 hover:underline text-sm"
                            >
                              Ver en Trello
                            </a>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default DebugPage; 