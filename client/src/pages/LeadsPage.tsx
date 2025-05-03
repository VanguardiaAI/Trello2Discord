import { useState, useEffect } from 'react';
import axios from 'axios';
import { AlertCircle, Download, RefreshCw, Search, X, Users, MapPin, Mail, Save, Edit } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

interface Lead {
  place_id: string;
  name: string;
  address: string;
  phone: string;
  email: string;
  website: string;
  rating: number;
  source: string;
}

interface Place {
  place_id: string;
  name: string;
  address: string;
  rating: number;
  location: {
    lat: number;
    lng: number;
  };
}

type Tab = 'search' | 'leads';

const LeadsPage = () => {
  // Estado para las pestañas
  const [activeTab, setActiveTab] = useState<Tab>('search');
  
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [searchResults, setSearchResults] = useState<Place[]>([]);
  const [searchLoading, setSearchLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState<string>('');
  const [address, setAddress] = useState<string>('');
  const [radius, setRadius] = useState<number>(5000);
  const [selectedPlaces, setSelectedPlaces] = useState<Place[]>([]);
  const [importing, setImporting] = useState<boolean>(false);
  const [nextPageToken, setNextPageToken] = useState<string | null>(null);
  
  // Estado para edición de email
  const [editingLeadId, setEditingLeadId] = useState<string | null>(null);
  const [editingEmail, setEditingEmail] = useState<string>('');
  const [savingEmail, setSavingEmail] = useState<boolean>(false);

  const fetchLeads = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/leads`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setLeads(response.data);
      setError(null);
    } catch (err) {
      console.error('Error al obtener leads:', err);
      setError('Error al cargar leads. Inténtalo de nuevo más tarde.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, []);

  const handleSearch = async () => {
    if (!query || !address) {
      setError('Se requieren el término de búsqueda y la dirección.');
      return;
    }

    try {
      setSearchLoading(true);
      setError(null);
      const token = localStorage.getItem('token');
      
      const params = new URLSearchParams({
        query,
        address,
        radius: radius.toString()
      });
      
      if (nextPageToken) {
        params.append('next_page_token', nextPageToken);
      }
      
      const response = await axios.get(`${API_URL}/places/search?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (nextPageToken) {
        setSearchResults([...searchResults, ...response.data.results]);
      } else {
        setSearchResults(response.data.results);
      }
      
      setNextPageToken(response.data.next_page_token || null);
    } catch (err) {
      console.error('Error en la búsqueda:', err);
      setError('Error al buscar negocios. Verifica tu conexión e inténtalo de nuevo.');
    } finally {
      setSearchLoading(false);
    }
  };

  const handleLoadMore = () => {
    if (nextPageToken) {
      handleSearch();
    }
  };

  const togglePlaceSelection = (place: Place) => {
    if (selectedPlaces.some(p => p.place_id === place.place_id)) {
      setSelectedPlaces(selectedPlaces.filter(p => p.place_id !== place.place_id));
    } else {
      setSelectedPlaces([...selectedPlaces, place]);
    }
  };

  const isPlaceSelected = (place_id: string) => {
    return selectedPlaces.some(p => p.place_id === place_id);
  };

  const handleImportLeads = async () => {
    if (selectedPlaces.length === 0) {
      setError('Selecciona al menos un negocio para importar.');
      return;
    }

    try {
      setImporting(true);
      setError(null);
      const token = localStorage.getItem('token');
      
      console.log(`Obteniendo detalles para ${selectedPlaces.length} lugares seleccionados`);
      
      // Primero, obtenemos los detalles completos de cada lugar
      const placesWithDetails = await Promise.all(
        selectedPlaces.map(async (place) => {
          try {
            console.log(`Pidiendo detalles para: ${place.place_id}`);
            const response = await axios.get(`${API_URL}/places/details/${place.place_id}`, {
              headers: { Authorization: `Bearer ${token}` }
            });
            
            // Verificar si tenemos un place_id en la respuesta
            const details = response.data;
            if (!details.place_id) {
              console.warn(`Añadiendo place_id faltante para: ${place.place_id}`);
              details.place_id = place.place_id;
            }
            
            console.log(`Detalles recibidos para: ${place.place_id}`, details);
            return details;
          } catch (error) {
            console.error(`Error al obtener detalles para ${place.place_id}:`, error);
            // Si falla al obtener detalles, devolvemos un objeto mínimo con el place_id
            return {
              place_id: place.place_id,
              name: place.name,
              address: place.address,
              rating: place.rating
            };
          }
        })
      );
      
      console.log(`Datos a importar:`, placesWithDetails);
      
      // Verificar que todos los lugares tienen place_id
      const validPlaces = placesWithDetails.filter(place => place && place.place_id);
      
      if (validPlaces.length === 0) {
        setError('No se pudieron obtener detalles válidos de ningún lugar.');
        setImporting(false);
        return;
      }
      
      console.log(`Enviando ${validPlaces.length} lugares para importar`);
      
      // Luego importamos los lugares a la base de datos
      const response = await axios.post(
        `${API_URL}/places/import`, 
        validPlaces,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      setSelectedPlaces([]);
      fetchLeads();
      
      // Mostramos un mensaje de éxito temporal
      alert(`${response.data.message}\nImportados: ${response.data.insertados}\nOmitidos: ${response.data.omitidos}`);
      
      // Cambiar a la pestaña de Mis Leads después de importar exitosamente
      if (response.data.insertados > 0) {
        setActiveTab('leads');
      }
      
    } catch (err: any) {
      console.error('Error al importar leads:', err);
      const errorMsg = err.response?.data?.error || 'Error al importar leads. Inténtalo de nuevo más tarde.';
      setError(errorMsg);
    } finally {
      setImporting(false);
    }
  };

  const handleExportCSV = async () => {
    try {
      const token = localStorage.getItem('token');
      
      // Hacer la solicitud para exportar leads
      const response = await axios.get(`${API_URL}/leads/export`, {
        headers: { 
          Authorization: `Bearer ${token}`,
        },
        responseType: 'blob'
      });
      
      // Crear un objeto URL para el blob
      const url = window.URL.createObjectURL(new Blob([response.data]));
      
      // Crear un elemento de enlace temporal
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'leads.csv');
      
      // Agregar, hacer clic y luego eliminar el enlace
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
    } catch (err) {
      console.error('Error al exportar leads:', err);
      setError('Error al exportar leads. Inténtalo de nuevo más tarde.');
    }
  };

  // Función para comenzar a editar el email de un lead
  const startEditingEmail = (lead: Lead) => {
    setEditingLeadId(lead.place_id);
    setEditingEmail(lead.email || '');
  };

  // Función para guardar el email editado
  const saveEmail = async (leadId: string) => {
    try {
      setSavingEmail(true);
      const token = localStorage.getItem('token');
      
      await axios.put(
        `${API_URL}/leads/${leadId}`, 
        { email: editingEmail },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Actualizar el lead en el estado local
      setLeads(leads.map(lead => 
        lead.place_id === leadId 
          ? { ...lead, email: editingEmail } 
          : lead
      ));
      
      setEditingLeadId(null);
      setEditingEmail('');
      setError(null);
    } catch (err) {
      console.error('Error al guardar email:', err);
      setError('Error al guardar el email. Inténtalo de nuevo más tarde.');
    } finally {
      setSavingEmail(false);
    }
  };

  // Función para cancelar la edición
  const cancelEditingEmail = () => {
    setEditingLeadId(null);
    setEditingEmail('');
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Leads</h1>
        <div className="flex gap-2">
          {activeTab === 'leads' && (
            <>
              <button 
                onClick={fetchLeads} 
                className="flex items-center px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                <RefreshCw className="w-4 h-4 mr-2" /> Actualizar
              </button>
              <button 
                onClick={handleExportCSV} 
                disabled={leads.length === 0}
                className={`flex items-center px-3 py-2 rounded-md ${
                  leads.length > 0 
                    ? 'bg-green-600 text-white hover:bg-green-700' 
                    : 'bg-gray-400 text-gray-200 cursor-not-allowed'
                }`}
              >
                <Download className="w-4 h-4 mr-2" /> Exportar CSV
              </button>
            </>
          )}
        </div>
      </div>

      {/* Navegación por pestañas */}
      <div className="mb-6 border-b border-gray-200">
        <div className="flex -mb-px">
          <button
            onClick={() => setActiveTab('search')}
            className={`px-6 py-3 font-medium text-sm flex items-center ${
              activeTab === 'search'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <MapPin className="w-4 h-4 mr-2" />
            Buscar Leads
          </button>
          <button
            onClick={() => setActiveTab('leads')}
            className={`px-6 py-3 font-medium text-sm flex items-center ${
              activeTab === 'leads'
                ? 'border-b-2 border-blue-500 text-blue-600'
                : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <Users className="w-4 h-4 mr-2" />
            Mis Leads {leads.length > 0 && `(${leads.length})`}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4 flex items-start">
          <AlertCircle className="w-5 h-5 mr-2 mt-0.5" />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto">
            <X className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Contenido de la pestaña de búsqueda */}
      {activeTab === 'search' && (
        <div>
          <div className="bg-white shadow-md rounded-lg p-6 mb-8">
            <h2 className="text-xl font-semibold mb-4">Buscar Negocios</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Término de búsqueda
                </label>
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Ej: Agencia de Marketing"
                  className="w-full p-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Dirección o Ciudad
                </label>
                <input
                  type="text"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="Ej: Madrid, España"
                  className="w-full p-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Radio (metros)
                </label>
                <input
                  type="number"
                  value={radius}
                  onChange={(e) => setRadius(Number(e.target.value))}
                  min="1000"
                  max="50000"
                  step="1000"
                  className="w-full p-2 border border-gray-300 rounded-md"
                />
              </div>
            </div>
            <div className="flex justify-end">
              <button
                onClick={handleSearch}
                disabled={searchLoading || !query || !address}
                className={`flex items-center px-4 py-2 rounded-md ${
                  !searchLoading && query && address
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-400 text-gray-200 cursor-not-allowed'
                }`}
              >
                {searchLoading ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Buscando...
                  </>
                ) : (
                  <>
                    <Search className="w-4 h-4 mr-2" />
                    Buscar
                  </>
                )}
              </button>
            </div>
          </div>

          {searchResults.length > 0 && (
            <div className="bg-white shadow-md rounded-lg p-6 mb-8">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold">Resultados de búsqueda</h2>
                <div className="flex gap-2">
                  <button
                    onClick={() => setSelectedPlaces([])}
                    disabled={selectedPlaces.length === 0}
                    className={`px-3 py-1 text-sm rounded ${
                      selectedPlaces.length > 0
                        ? 'bg-gray-200 hover:bg-gray-300'
                        : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    }`}
                  >
                    Deseleccionar todos
                  </button>
                  <button
                    onClick={() => setSelectedPlaces([...searchResults])}
                    disabled={searchResults.length === 0}
                    className="px-3 py-1 text-sm bg-gray-200 hover:bg-gray-300 rounded"
                  >
                    Seleccionar todos
                  </button>
                  <button
                    onClick={handleImportLeads}
                    disabled={importing || selectedPlaces.length === 0}
                    className={`flex items-center px-3 py-1 text-sm rounded ${
                      !importing && selectedPlaces.length > 0
                        ? 'bg-green-600 text-white hover:bg-green-700'
                        : 'bg-gray-400 text-gray-200 cursor-not-allowed'
                    }`}
                  >
                    {importing ? 'Importando...' : `Importar (${selectedPlaces.length})`}
                  </button>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Seleccionar
                      </th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Nombre
                      </th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Dirección
                      </th>
                      <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Rating
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {searchResults.map((place) => (
                      <tr 
                        key={place.place_id}
                        onClick={() => togglePlaceSelection(place)}
                        className={`hover:bg-gray-50 cursor-pointer ${
                          isPlaceSelected(place.place_id) ? 'bg-blue-50' : ''
                        }`}
                      >
                        <td className="px-6 py-4 whitespace-nowrap">
                          <input
                            type="checkbox"
                            checked={isPlaceSelected(place.place_id)}
                            onChange={() => togglePlaceSelection(place)}
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                          />
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">{place.name}</div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="text-sm text-gray-500">{place.address}</div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-900">
                            {place.rating ? `${place.rating} / 5` : 'Sin rating'}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {nextPageToken && (
                <div className="mt-4 flex justify-center">
                  <button
                    onClick={handleLoadMore}
                    disabled={searchLoading}
                    className={`px-4 py-2 rounded ${
                      !searchLoading
                        ? 'bg-blue-600 text-white hover:bg-blue-700'
                        : 'bg-gray-400 text-gray-200 cursor-not-allowed'
                    }`}
                  >
                    {searchLoading ? 'Cargando...' : 'Cargar más resultados'}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Contenido de la pestaña de mis leads */}
      {activeTab === 'leads' && (
        <div className="bg-white shadow-md rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Mis Leads ({leads.length})</h2>
          
          {loading ? (
            <div className="flex justify-center items-center h-40">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-700"></div>
            </div>
          ) : leads.length === 0 ? (
            <div className="text-center py-12 flex flex-col items-center">
              <div className="mb-4">
                <svg className="w-16 h-16 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path>
                </svg>
              </div>
              <p className="text-gray-500 mb-4">No tienes leads guardados.</p>
              <button 
                onClick={() => setActiveTab('search')} 
                className="bg-blue-600 text-white hover:bg-blue-700 px-4 py-2 rounded-md text-sm flex items-center"
              >
                <Search className="w-4 h-4 mr-2" />
                Buscar negocios
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 rounded-lg overflow-hidden">
                <thead className="bg-gray-100">
                  <tr>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                      Nombre
                    </th>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                      Teléfono
                    </th>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                      Email
                    </th>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                      Web
                    </th>
                    <th scope="col" className="px-6 py-4 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                      Dirección
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {leads.map((lead) => (
                    <tr key={lead.place_id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-gray-900">{lead.name}</div>
                      </td>
                      <td className="px-6 py-4">
                        {lead.phone ? (
                          <a href={`tel:${lead.phone}`} className="text-sm text-blue-600 hover:text-blue-800 flex items-center">
                            {lead.phone}
                          </a>
                        ) : (
                          <span className="text-sm text-gray-500">N/A</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {editingLeadId === lead.place_id ? (
                          <div className="flex items-center">
                            <input
                              type="email"
                              value={editingEmail}
                              onChange={(e) => setEditingEmail(e.target.value)}
                              className="w-full p-1 text-sm border border-gray-300 rounded-md"
                              placeholder="Agregar email"
                              autoFocus
                            />
                            <div className="flex ml-2">
                              <button
                                onClick={() => saveEmail(lead.place_id)}
                                disabled={savingEmail}
                                className="text-green-600 hover:text-green-800 mr-1"
                                title="Guardar"
                              >
                                <Save className="w-4 h-4" />
                              </button>
                              <button
                                onClick={cancelEditingEmail}
                                className="text-red-600 hover:text-red-800"
                                title="Cancelar"
                              >
                                <X className="w-4 h-4" />
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="flex items-center">
                            {lead.email ? (
                              <a href={`mailto:${lead.email}`} className="text-sm text-blue-600 hover:text-blue-800 flex items-center">
                                <Mail className="w-4 h-4 mr-1" />
                                {lead.email}
                              </a>
                            ) : (
                              <span className="text-sm text-gray-500">N/A</span>
                            )}
                            <button
                              onClick={() => startEditingEmail(lead)}
                              className="ml-2 text-gray-500 hover:text-gray-700"
                              title="Editar email"
                            >
                              <Edit className="w-4 h-4" />
                            </button>
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {lead.website ? (
                          <a 
                            href={lead.website} 
                            target="_blank" 
                            rel="noopener noreferrer" 
                            className="text-blue-600 hover:text-blue-800 text-sm hover:underline"
                          >
                            {new URL(lead.website).hostname}
                          </a>
                        ) : (
                          <span className="text-sm text-gray-500">N/A</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm text-gray-500">{lead.address || 'N/A'}</div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default LeadsPage; 