import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { AlertCircle, Download, RefreshCw, Search, X, Users, MapPin, Mail, Save, Edit, Database, ChevronRight, Trash2, Tag, MessageSquare, Check, Plus, Filter } from 'lucide-react';

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
  status?: string;
  labels?: string[];
  notes?: Note[];
  created_at?: string;
  updated_at?: string;
}

interface Note {
  id: number;
  content: string;
  created_at: string;
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

interface PlaceDetails extends Place {
  phone?: string;
  email?: string;
  website?: string;
  source?: string;
}

interface SearchState {
  query: string;
  address: string;
  radius: number;
}

interface Label {
  text: string;
  color?: string;
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
  const [searchHistory, setSearchHistory] = useState<SearchState[]>([]);
  const [totalResultsCount, setTotalResultsCount] = useState<number>(0);
  const [allResultsFetched, setAllResultsFetched] = useState<boolean>(false);
  
  // Estado para edición de email
  const [editingLeadId, setEditingLeadId] = useState<string | null>(null);
  const [editingEmail, setEditingEmail] = useState<string>('');
  const [savingEmail, setSavingEmail] = useState<boolean>(false);

  // Añadir nuevos estados para gestionar leads, etiquetas y notas
  const [selectedLeads, setSelectedLeads] = useState<string[]>([]);
  const [newNote, setNewNote] = useState<string>('');
  const [addingNoteToId, setAddingNoteToId] = useState<string | null>(null);
  const [editingNoteId, setEditingNoteId] = useState<number | null>(null);
  const [showNotePopup, setShowNotePopup] = useState<boolean>(false);
  const [availableLabels, setAvailableLabels] = useState<string[]>([]);
  const [defaultLabels] = useState<string[]>([
    'Número equivocado', 'No contestan', 'Interesado', 'No interesado', 
    'Por contactar', 'En seguimiento', 'Cliente potencial', 'Venta cerrada'
  ]);
  const [newLabelText, setNewLabelText] = useState<string>('');
  const [showLabelForm, setShowLabelForm] = useState<boolean>(false);
  const [showLabelsManagement, setShowLabelsManagement] = useState<boolean>(false);
  const [savingLabel, setSavingLabel] = useState<boolean>(false);
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [selectedLabels, setSelectedLabels] = useState<string[]>([]);
  const [statusOptions] = useState<string[]>([
    'Nuevo', 'Por contactar', 'Contactado', 'Interesado', 'No interesado', 'En seguimiento', 'Cliente'
  ]);
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [filterLabels, setFilterLabels] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState<boolean>(false);

  // Estado para gestionar qué lead está mostrando el selector de estado
  const [leadWithStatusSelector, setLeadWithStatusSelector] = useState<string | null>(null);

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
    fetchLabels();
  }, []);

  // Función para verificar si un lugar ya está en los leads guardados
  const isPlaceInLeads = (place_id: string) => {
    return leads.some(lead => lead.place_id === place_id);
  };

  const handleSearch = async (isNewSearch = true) => {
    if (!query || !address) {
      setError('Se requieren el término de búsqueda y la dirección.');
      return;
    }

    try {
      setSearchLoading(true);
      setError(null);
      const token = localStorage.getItem('token');
      
      // Si es una nueva búsqueda, guardamos el estado actual en el historial
      if (isNewSearch) {
        setSearchResults([]);
        setNextPageToken(null);
        setAllResultsFetched(false);
        
        // Guardamos la configuración de búsqueda actual
        const currentSearch: SearchState = {
          query,
          address,
          radius
        };
        setSearchHistory([...searchHistory, currentSearch]);
      }
      
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
        setSearchResults(prevResults => [...prevResults, ...response.data.results]);
      } else {
        setSearchResults(response.data.results);
      }
      
      // Actualizar contadores y token para la siguiente página
      setTotalResultsCount(prev => prev + response.data.results.length);
      
      if (response.data.next_page_token) {
        setNextPageToken(response.data.next_page_token);
      } else {
        setNextPageToken(null);
        setAllResultsFetched(true);
      }
    } catch (err) {
      console.error('Error en la búsqueda:', err);
      setError('Error al buscar negocios. Verifica tu conexión e inténtalo de nuevo.');
    } finally {
      setSearchLoading(false);
    }
  };

  // Función para cargar automáticamente todas las páginas disponibles
  const handleLoadAllResults = async () => {
    try {
      // Si ya estamos cargando o no hay nextPageToken, salimos
      if (searchLoading || !nextPageToken) return;
      
      // Mientras haya un nextPageToken, seguimos cargando
      while (nextPageToken && !searchLoading) {
        await handleSearch(false);
        
        // Esperamos un breve momento para evitar problemas de rate limiting
        await new Promise(resolve => setTimeout(resolve, 300));
      }
      
      setAllResultsFetched(true);
    } catch (err) {
      console.error('Error al cargar todos los resultados:', err);
      setError('Se produjo un error al cargar todos los resultados. Por favor, inténtalo de nuevo.');
    }
  };

  const handleLoadMore = () => {
    if (nextPageToken) {
      handleSearch(false);
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

  // Función para realizar una búsqueda completa (todas las estrategias combinadas)
  const handleFullSearch = () => {
    if (!query || !address) {
      setError('Se requieren el término de búsqueda y la dirección.');
      return;
    }
    
    try {
      setSearchLoading(true);
      setError(null);
      setSearchResults([]);
      setNextPageToken(null);
      setAllResultsFetched(false);
      
      const token = localStorage.getItem('token');
      
      // Guardamos la configuración de búsqueda actual
      const currentSearch: SearchState = {
        query,
        address,
        radius
      };
      setSearchHistory([...searchHistory, currentSearch]);
      
      const params = new URLSearchParams({
        query,
        address,
        radius: radius.toString()
      });
      
      // Llamar al endpoint de búsqueda completa
      axios.get(`${API_URL}/places/search/full?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(response => {
        setSearchResults(response.data.results);
        setNextPageToken(null);
        setAllResultsFetched(true);
        setTotalResultsCount(response.data.total_results || response.data.results.length);
      })
      .catch(err => {
        console.error('Error en la búsqueda completa:', err);
        setError('Error al buscar negocios con la estrategia completa. Verifica tu conexión e inténtalo de nuevo.');
      })
      .finally(() => {
        setSearchLoading(false);
      });
    } catch (err) {
      console.error('Error en la búsqueda completa:', err);
      setError('Error al buscar negocios. Verifica tu conexión e inténtalo de nuevo.');
      setSearchLoading(false);
    }
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
      const placesWithDetails: PlaceDetails[] = await Promise.all(
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
      const validPlaces = placesWithDetails.filter((place: PlaceDetails) => place && place.place_id);
      
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
      
      // Crear un enlace directo para la descarga con el token en el encabezado
      const downloadUrl = `${API_URL}/leads/export`;
      
      // Hacemos una solicitud fetch directa con los encabezados correspondientes
      const response = await fetch(downloadUrl, {
        method: 'GET',
        headers: { 
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`Error en la respuesta: ${response.status} ${response.statusText}`);
      }
      
      // Obtener el blob de la respuesta
      const blob = await response.blob();
      
      // Crear un objeto URL para el blob
      const url = window.URL.createObjectURL(blob);
      
      // Crear un elemento de enlace temporal
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'leads.csv');
      
      // Agregar, hacer clic y luego eliminar el enlace
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // Limpiar el objeto URL
      window.URL.revokeObjectURL(url);
      
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

  // Función para obtener todas las etiquetas disponibles
  const fetchLabels = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/leads/labels`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      setAvailableLabels(response.data);
    } catch (err) {
      console.error('Error al obtener etiquetas:', err);
    }
  };

  // Función para guardar una etiqueta personalizada en la base de datos
  const saveCustomLabel = async (labelText: string) => {
    if (!labelText.trim()) return;
    
    try {
      setSavingLabel(true);
      const token = localStorage.getItem('token');
      
      await axios.post(
        `${API_URL}/leads/labels`,
        { label: labelText.trim() },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Actualizar la lista de etiquetas disponibles
      fetchLabels();
      
      setNewLabelText('');
      setShowLabelForm(false);
      setError(null);
    } catch (err) {
      console.error('Error al guardar etiqueta:', err);
      setError('Error al guardar etiqueta. Inténtalo de nuevo más tarde.');
    } finally {
      setSavingLabel(false);
    }
  };

  // Función para eliminar una etiqueta personalizada
  const deleteCustomLabel = async (labelText: string) => {
    try {
      setSavingLabel(true);
      const token = localStorage.getItem('token');
      
      await axios.delete(
        `${API_URL}/leads/labels/${encodeURIComponent(labelText)}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Actualizar la lista de etiquetas disponibles
      fetchLabels();
      
      setError(null);
    } catch (err) {
      console.error('Error al eliminar etiqueta:', err);
      setError('Error al eliminar etiqueta. Inténtalo de nuevo más tarde.');
    } finally {
      setSavingLabel(false);
    }
  };

  // Función para añadir una etiqueta personalizada
  const addCustomLabel = () => {
    if (!newLabelText.trim()) return;
    
    // Guardar la etiqueta en la base de datos
    saveCustomLabel(newLabelText.trim());
  };

  // Función para seleccionar/deseleccionar un lead
  const toggleLeadSelection = (leadId: string) => {
    if (selectedLeads.includes(leadId)) {
      setSelectedLeads(selectedLeads.filter(id => id !== leadId));
    } else {
      setSelectedLeads([...selectedLeads, leadId]);
    }
  };

  // Función para seleccionar todos los leads
  const selectAllLeads = () => {
    if (selectedLeads.length === leads.length) {
      setSelectedLeads([]);
    } else {
      setSelectedLeads(leads.map(lead => lead.place_id));
    }
  };

  // Función para eliminar leads seleccionados
  const deleteSelectedLeads = async () => {
    if (selectedLeads.length === 0) return;
    
    if (!confirm(`¿Estás seguro de que quieres eliminar ${selectedLeads.length} leads?`)) {
      return;
    }
    
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      await axios.post(
        `${API_URL}/leads/batch/delete`,
        { leads: selectedLeads },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Actualizar la lista local
      setLeads(leads.filter(lead => !selectedLeads.includes(lead.place_id)));
      setSelectedLeads([]);
      setError(null);
    } catch (err) {
      console.error('Error al eliminar leads:', err);
      setError('Error al eliminar leads. Inténtalo de nuevo más tarde.');
    } finally {
      setLoading(false);
    }
  };

  // Función para aplicar etiquetas a los leads seleccionados
  const applyLabelsToSelected = async (labels: string[]) => {
    if (selectedLeads.length === 0 || labels.length === 0) return;
    
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      await axios.post(
        `${API_URL}/leads/batch/update`,
        { 
          leads: selectedLeads,
          add_labels: labels
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Actualizar la lista local
      setLeads(leads.map(lead => {
        if (selectedLeads.includes(lead.place_id)) {
          const updatedLabels = [...(lead.labels || [])];
          labels.forEach(label => {
            if (!updatedLabels.includes(label)) {
              updatedLabels.push(label);
            }
          });
          return { ...lead, labels: updatedLabels };
        }
        return lead;
      }));
      
      setError(null);
    } catch (err) {
      console.error('Error al aplicar etiquetas:', err);
      setError('Error al aplicar etiquetas. Inténtalo de nuevo más tarde.');
    } finally {
      setLoading(false);
    }
  };

  // Función para actualizar el estado de los leads seleccionados
  const updateStatusForSelected = async (status: string) => {
    if (selectedLeads.length === 0 || !status) return;
    
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      await axios.post(
        `${API_URL}/leads/batch/update`,
        { 
          leads: selectedLeads,
          status
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Actualizar la lista local
      setLeads(leads.map(lead => {
        if (selectedLeads.includes(lead.place_id)) {
          return { ...lead, status };
        }
        return lead;
      }));
      
      setSelectedStatus('');
      setError(null);
    } catch (err) {
      console.error('Error al actualizar estado:', err);
      setError('Error al actualizar estado. Inténtalo de nuevo más tarde.');
    } finally {
      setLoading(false);
    }
  };

  // Función para añadir o actualizar una nota en un lead
  const addOrUpdateNoteToLead = async (leadId: string) => {
    if (!newNote.trim()) return;
    
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      // Si estamos editando una nota existente
      if (editingNoteId !== null) {
        // Eliminar la nota anterior
        await axios.delete(
          `${API_URL}/leads/${leadId}/notes/${editingNoteId}`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
      }
      
      // Añadir la nueva nota
      const response = await axios.post(
        `${API_URL}/leads/${leadId}/notes`,
        { content: newNote },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Actualizar la lista local
      setLeads(leads.map(lead => {
        if (lead.place_id === leadId) {
          let updatedNotes;
          
          if (editingNoteId !== null) {
            // Reemplazar la nota editada
            updatedNotes = (lead.notes || []).filter(note => note.id !== editingNoteId);
            updatedNotes.push(response.data.note);
          } else {
            // Si no hay notas previas o estamos añadiendo una nueva
            updatedNotes = lead.notes && lead.notes.length > 0 
              ? [response.data.note] // Reemplazar con la nueva nota
              : [response.data.note]; // Añadir la primera nota
          }
          
          return { ...lead, notes: updatedNotes };
        }
        return lead;
      }));
      
      setNewNote('');
      setAddingNoteToId(null);
      setEditingNoteId(null);
      setShowNotePopup(false);
      setError(null);
    } catch (err) {
      console.error('Error al añadir/actualizar nota:', err);
      setError('Error al gestionar la nota. Inténtalo de nuevo más tarde.');
    } finally {
      setLoading(false);
    }
  };

  // Función para comenzar a editar una nota
  const startEditingNote = (leadId: string, note: Note) => {
    setAddingNoteToId(leadId);
    setEditingNoteId(note.id);
    setNewNote(note.content);
    setShowNotePopup(true);
  };

  // Función para cancelar la edición de una nota
  const cancelEditingNote = () => {
    setAddingNoteToId(null);
    setEditingNoteId(null);
    setNewNote('');
    setShowNotePopup(false);
  };

  // Función para abrir el popup para añadir una nota
  const openAddNotePopup = (leadId: string) => {
    setAddingNoteToId(leadId);
    setEditingNoteId(null);
    setNewNote('');
    setShowNotePopup(true);
  };

  // Función para eliminar una nota de un lead
  const deleteNoteFromLead = async (leadId: string, noteId: number) => {
    try {
      setLoading(true);
      const token = localStorage.getItem('token');
      
      await axios.delete(
        `${API_URL}/leads/${leadId}/notes/${noteId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      // Actualizar la lista local
      setLeads(leads.map(lead => {
        if (lead.place_id === leadId) {
          const updatedNotes = (lead.notes || []).filter(note => note.id !== noteId);
          return { ...lead, notes: updatedNotes };
        }
        return lead;
      }));
      
      setError(null);
    } catch (err) {
      console.error('Error al eliminar nota:', err);
      setError('Error al eliminar nota. Inténtalo de nuevo más tarde.');
    } finally {
      setLoading(false);
    }
  };

  // Función para filtrar leads según estado y etiquetas
  const getFilteredLeads = () => {
    return leads.filter(lead => {
      // Filtrar por estado
      if (filterStatus && lead.status !== filterStatus) {
        return false;
      }
      
      // Filtrar por etiquetas (debe tener todas las etiquetas seleccionadas)
      if (filterLabels.length > 0) {
        const leadLabels = lead.labels || [];
        return filterLabels.every(label => leadLabels.includes(label));
      }
      
      return true;
    });
  };

  // Función para subdividir la búsqueda en áreas más pequeñas
  const handleSubdivideSearch = () => {
    if (!query || !address) {
      setError('Se requieren el término de búsqueda y la dirección.');
      return;
    }
    
    try {
      setSearchLoading(true);
      setError(null);
      setSearchResults([]);
      setNextPageToken(null);
      setAllResultsFetched(false);
      
      const token = localStorage.getItem('token');
      
      // Guardamos la configuración de búsqueda actual
      const currentSearch: SearchState = {
        query,
        address,
        radius
      };
      setSearchHistory([...searchHistory, currentSearch]);
      
      const params = new URLSearchParams({
        query,
        address,
        radius: radius.toString()
      });
      
      // Llamar al endpoint de búsqueda subdividida
      axios.get(`${API_URL}/places/search/subdivide?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      .then(response => {
        setSearchResults(response.data.results);
        // No hay token en búsquedas subdivididas
        setNextPageToken(null);
        setAllResultsFetched(true);
        setTotalResultsCount(response.data.total_results || response.data.results.length);
      })
      .catch(err => {
        console.error('Error en la búsqueda subdividida:', err);
        setError('Error al buscar negocios con la estrategia subdividida. Verifica tu conexión e inténtalo de nuevo.');
      })
      .finally(() => {
        setSearchLoading(false);
      });
    } catch (err) {
      console.error('Error en la búsqueda subdividida:', err);
      setError('Error al buscar negocios. Verifica tu conexión e inténtalo de nuevo.');
      setSearchLoading(false);
    }
  };

  // Añadir un componente reutilizable para seleccionar estado
  const StatusSelector = ({ lead, showSelector, setShowSelector }: { 
    lead: Lead, 
    showSelector: boolean, 
    setShowSelector: (show: boolean) => void 
  }) => {
    const [loading, setLoading] = useState(false);
    const [selectedStatus, setSelectedStatus] = useState(lead.status || 'Nuevo');
    const selectorRef = useRef<HTMLDivElement>(null);

    // Hook para cerrar el selector al hacer clic fuera
    useEffect(() => {
      const handleClickOutside = (event: MouseEvent) => {
        if (selectorRef.current && !selectorRef.current.contains(event.target as Node)) {
          setShowSelector(false);
        }
      };

      if (showSelector) {
        document.addEventListener('mousedown', handleClickOutside);
      }
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }, [showSelector, setShowSelector]);

    const handleChangeStatus = async (status: string) => {
      try {
        setLoading(true);
        const token = localStorage.getItem('token');
        
        await axios.put(
          `${API_URL}/leads/${lead.place_id}`,
          { status },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        
        // Actualizar el lead en el estado local
        setLeads(prevLeads => prevLeads.map(l => 
          l.place_id === lead.place_id ? { ...l, status } : l
        ));
        
        setShowSelector(false);
      } catch (err) {
        console.error('Error al cambiar estado:', err);
        setError('Error al cambiar estado. Inténtalo de nuevo más tarde.');
      } finally {
        setLoading(false);
      }
  };

  return (
      <div className="relative" ref={selectorRef}>
        {showSelector && (
          <div className="absolute top-full left-0 z-10 mt-1 w-48 bg-white rounded-md shadow-lg border border-gray-200">
            <div className="py-1">
              {statusOptions.map(status => (
              <button 
                  key={status}
                  onClick={() => handleChangeStatus(status)}
                  disabled={loading}
                  className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 ${
                    lead.status === status ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
                  }`}
                >
                  {status}
              </button>
              ))}
            </div>
            {loading && (
              <div className="flex justify-center py-2">
                <svg className="animate-spin h-5 w-5 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
          )}
        </div>
        )}
      </div>
    );
  };

  return (
    <div className="container-fluid w-full px-2 py-8">

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
            <div className="flex flex-wrap gap-2 justify-end">
              <button
                onClick={() => handleSearch(true)}
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
                    Búsqueda Estándar
                  </>
                )}
              </button>
              
              <button
                onClick={handleFullSearch}
                disabled={searchLoading || !query || !address}
                title="Usa todas las estrategias combinadas para obtener el máximo de resultados"
                className={`flex items-center px-4 py-2 rounded-md ${
                  !searchLoading && query && address
                    ? 'bg-purple-600 text-white hover:bg-purple-700'
                    : 'bg-gray-400 text-gray-200 cursor-not-allowed'
                }`}
              >
                <Database className="w-4 h-4 mr-2" />
                Búsqueda Completa
              </button>
            </div>
          </div>

          {searchResults.length > 0 && (
            <div className="bg-white shadow-md rounded-lg p-6 mb-8">
              <div className="flex justify-between items-center mb-4">
                <div>
                  <h2 className="text-xl font-semibold">Resultados de búsqueda ({searchResults.length})</h2>
                  {!allResultsFetched && nextPageToken && (
                    <p className="text-sm text-gray-500">Hay más resultados disponibles</p>
                  )}
                  {allResultsFetched && (
                    <p className="text-sm text-green-600">Todos los resultados cargados</p>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
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
                    onClick={handleLoadAllResults}
                    disabled={searchLoading || allResultsFetched || !nextPageToken}
                    className={`flex items-center px-3 py-1 text-sm rounded ${
                      !searchLoading && nextPageToken && !allResultsFetched
                        ? 'bg-purple-600 text-white hover:bg-purple-700'
                        : 'bg-gray-400 text-gray-200 cursor-not-allowed'
                    }`}
                  >
                    {searchLoading ? 'Cargando...' : 'Cargar Todos'}
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
                        Estado
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
                          {isPlaceInLeads(place.place_id) ? (
                            <span className="px-2 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800 flex items-center">
                              <Database className="w-3 h-3 mr-1" /> Guardado
                            </span>
                          ) : (
                            <span className="text-xs text-gray-500">Nuevo</span>
                          )}
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
              
              {nextPageToken && !allResultsFetched && (
                <div className="mt-4 flex justify-center">
                  <button
                    onClick={handleLoadMore}
                    disabled={searchLoading}
                    className={`flex items-center px-4 py-2 rounded ${
                      !searchLoading
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
                        Cargando...
                      </>
                    ) : (
                      <>
                        Cargar más resultados <ChevronRight className="w-4 h-4 ml-1" />
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Contenido de la pestaña de mis leads */}
      {activeTab === 'leads' && (
        <div className="bg-white shadow-md rounded-lg p-4">
          <div className="flex flex-wrap justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Mis Leads ({leads.length})</h2>
            
            <div className="flex flex-wrap gap-2">
              <button 
                onClick={() => setShowFilters(!showFilters)}
                className="flex items-center px-3 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200"
              >
                <Filter className="w-4 h-4 mr-2" /> Filtros
              </button>
              
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
            </div>
          </div>
          
          {showFilters && (
            <div className="mb-6 p-4 border border-gray-200 rounded-md bg-gray-50">
              <h3 className="font-medium mb-3">Filtros</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Estado</label>
                  <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="w-full p-2 border border-gray-300 rounded-md"
                  >
                    <option value="">Todos</option>
                    {statusOptions.map(option => (
                      <option key={option} value={option}>{option}</option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Etiquetas</label>
                  <div className="flex flex-wrap gap-2">
                    {availableLabels.slice(0, 6).map(label => (
                      <button
                        key={label}
                        onClick={() => {
                          if (filterLabels.includes(label)) {
                            setFilterLabels(filterLabels.filter(l => l !== label));
                          } else {
                            setFilterLabels([...filterLabels, label]);
                          }
                        }}
                        className={`px-2 py-1 text-xs rounded-full ${
                          filterLabels.includes(label)
                            ? 'bg-blue-100 text-blue-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              
              <div className="flex justify-end mt-3">
                <button
                  onClick={() => {
                    setFilterStatus('');
                    setFilterLabels([]);
                  }}
                  className="px-3 py-1 text-sm bg-gray-200 hover:bg-gray-300 rounded mr-2"
                >
                  Limpiar filtros
                </button>
                <button
                  onClick={() => setShowFilters(false)}
                  className="px-3 py-1 text-sm bg-blue-600 text-white hover:bg-blue-700 rounded"
                >
                  Aplicar
                </button>
              </div>
            </div>
          )}
          
          {selectedLeads.length > 0 && (
            <div className="mb-6 p-4 border border-gray-200 rounded-md bg-blue-50">
              <div className="flex justify-between items-center mb-3">
                <h3 className="font-medium">
                  {selectedLeads.length} {selectedLeads.length === 1 ? 'lead seleccionado' : 'leads seleccionados'}
                </h3>
                <button
                  onClick={() => setSelectedLeads([])}
                  className="text-gray-600 hover:text-gray-800"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Cambiar estado
                  </label>
                  <div className="flex">
                    <select
                      value={selectedStatus}
                      onChange={(e) => setSelectedStatus(e.target.value)}
                      className="w-full p-2 border border-gray-300 rounded-l-md"
                    >
                      <option value="">Seleccionar estado</option>
                      {statusOptions.map(option => (
                        <option key={option} value={option}>{option}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => updateStatusForSelected(selectedStatus)}
                      disabled={!selectedStatus}
                      className={`px-3 py-2 rounded-r-md ${
                        selectedStatus
                          ? 'bg-blue-600 text-white hover:bg-blue-700'
                          : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      }`}
                    >
                      <Check className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Añadir etiquetas
                  </label>
                  <div className="flex flex-wrap gap-2 mb-2">
                    {availableLabels.slice(0, 6).map(label => (
                      <button
                        key={label}
                        onClick={() => applyLabelsToSelected([label])}
                        className="px-2 py-1 text-xs bg-gray-200 hover:bg-gray-300 rounded-full"
                      >
                        {label}
                      </button>
                    ))}
                  
                    {availableLabels.length > 6 && (
                      <button
                        onClick={() => setShowLabelsManagement(true)}
                        className="px-2 py-1 text-xs bg-blue-100 text-blue-700 hover:bg-blue-200 rounded-full flex items-center"
                      >
                        <Plus className="w-3 h-3 mr-1" /> Más...
                      </button>
                    )}
                  </div>
                  
                  {showLabelForm ? (
                    <div className="flex mt-2">
                      <input
                        type="text"
                        value={newLabelText}
                        onChange={(e) => setNewLabelText(e.target.value)}
                        placeholder="Nueva etiqueta"
                        className="p-2 text-sm border border-gray-300 rounded-l-md flex-grow"
                        autoFocus
                      />
                      <div className="flex">
                        <button
                          onClick={addCustomLabel}
                          disabled={!newLabelText.trim() || savingLabel}
                          className={`px-3 py-2 ${
                            !newLabelText.trim() || savingLabel
                              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                              : 'bg-green-600 text-white hover:bg-green-700'
                          }`}
                        >
                          {savingLabel ? (
                            <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                          ) : (
                            <Check className="w-4 h-4" />
                          )}
                        </button>
                        <button
                          onClick={() => {
                            setShowLabelForm(false);
                            setNewLabelText('');
                          }}
                          className="px-3 py-2 bg-red-600 text-white hover:bg-red-700 rounded-r-md"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setShowLabelForm(true)}
                      className="mt-2 px-3 py-1 text-sm bg-gray-100 text-gray-700 hover:bg-gray-200 rounded-md flex items-center"
                    >
                      <Plus className="w-3 h-3 mr-1" /> Nueva etiqueta
                    </button>
                  )}
                </div>
              </div>
              
              <div className="flex justify-end">
                <button
                  onClick={deleteSelectedLeads}
                  className="flex items-center px-3 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
                >
                  <Trash2 className="w-4 h-4 mr-2" /> Eliminar seleccionados
                </button>
              </div>
            </div>
          )}
          
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
            <div className="overflow-x-auto w-full">
              <table className="min-w-full divide-y divide-gray-200 rounded-lg overflow-hidden">
                <thead className="bg-gray-100">
                  <tr>
                    <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                      <div className="flex items-center">
                        <input
                          type="checkbox"
                          checked={selectedLeads.length === getFilteredLeads().length && leads.length > 0}
                          onChange={selectAllLeads}
                          className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mr-2"
                        />
                      Nombre
                      </div>
                    </th>
                    <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                      Estado
                    </th>
                    <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                      Etiquetas
                    </th>
                    <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                      Teléfono
                    </th>
                    <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                      Email
                    </th>
                    <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                      Web
                    </th>
                    <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                      Notas
                    </th>
                    <th scope="col" className="px-4 py-3 text-left text-xs font-medium text-gray-600 uppercase tracking-wider">
                      Acciones
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {getFilteredLeads().map((lead) => (
                    <tr key={lead.place_id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-4">
                        <div className="flex items-center">
                          <input
                            type="checkbox"
                            checked={selectedLeads.includes(lead.place_id)}
                            onChange={() => toggleLeadSelection(lead.place_id)}
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mr-2"
                          />
                        <div className="text-sm font-medium text-gray-900">{lead.name}</div>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <div className="relative">
                          <button 
                            onClick={(e) => {
                              e.stopPropagation();
                              setLeadWithStatusSelector(leadWithStatusSelector === lead.place_id ? null : lead.place_id);
                            }}
                            className="w-full text-left focus:outline-none"
                          >
                            <span className={`px-2 py-1 text-xs rounded-full ${
                              lead.status === 'Interesado' ? 'bg-green-100 text-green-800' :
                              lead.status === 'No interesado' ? 'bg-red-100 text-red-800' :
                              lead.status === 'Contactado' ? 'bg-blue-100 text-blue-800' :
                              lead.status === 'Por contactar' ? 'bg-yellow-100 text-yellow-800' :
                              lead.status === 'En seguimiento' ? 'bg-purple-100 text-purple-800' :
                              lead.status === 'Cliente' ? 'bg-indigo-100 text-indigo-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {lead.status || 'Nuevo'}
                            </span>
                          </button>
                          {leadWithStatusSelector === lead.place_id && (
                            <StatusSelector 
                              lead={lead} 
                              showSelector={true} 
                              setShowSelector={(show) => {
                                if (!show) setLeadWithStatusSelector(null);
                              }} 
                            />
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex flex-wrap gap-1">
                          {(lead.labels || []).map((label, index) => (
                            <span 
                              key={index} 
                              className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded-full"
                            >
                              {label}
                            </span>
                          ))}
                          {(lead.labels || []).length === 0 && (
                            <div className="flex items-center">
                              <span className="text-xs text-gray-500 mr-2">Sin etiquetas</span>
                              <button
                                onClick={() => {
                                  toggleLeadSelection(lead.place_id);
                                  setShowLabelsManagement(true);
                                }}
                                className="text-blue-500 hover:text-blue-700 text-xs flex items-center"
                                title="Añadir etiquetas"
                              >
                                <Plus className="w-3 h-3" />
                              </button>
                            </div>
                          )}
                          <button
                            onClick={() => {
                              toggleLeadSelection(lead.place_id);
                              setShowLabelsManagement(true);
                            }}
                            className="ml-1 text-blue-500 hover:text-blue-700 text-xs"
                            title="Gestionar etiquetas"
                          >
                            <Tag className="w-3 h-3" />
                          </button>
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        {lead.phone ? (
                          <a href={`tel:${lead.phone}`} className="text-sm text-blue-600 hover:text-blue-800 flex items-center">
                            {lead.phone}
                          </a>
                        ) : (
                          <span className="text-sm text-gray-500">N/A</span>
                        )}
                      </td>
                      <td className="px-4 py-4">
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
                      <td className="px-4 py-4">
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
                      <td className="px-4 py-4">
                        <div>
                          {(lead.notes || []).length > 0 ? (
                            <div className="mb-1 group relative">
                              <div className="text-sm text-gray-500 truncate max-w-xs">
                                {lead.notes && lead.notes[0] ? lead.notes[0].content : ''}
                              </div>
                              <div className="flex mt-1 gap-2">
                                <button
                                  onClick={() => lead.notes && lead.notes[0] && startEditingNote(lead.place_id, lead.notes[0])}
                                  className="text-blue-500 hover:text-blue-700 text-xs flex items-center"
                                >
                                  <Edit className="w-3 h-3 mr-1" /> Editar
                                </button>
                                <button
                                  onClick={() => lead.notes && lead.notes[0] && deleteNoteFromLead(lead.place_id, lead.notes[0].id)}
                                  className="text-red-500 hover:text-red-700 text-xs flex items-center"
                                >
                                  <Trash2 className="w-3 h-3 mr-1" /> Eliminar
                                </button>
                              </div>
                            </div>
                          ) : (
                            <button
                              onClick={() => openAddNotePopup(lead.place_id)}
                              className="text-gray-500 hover:text-gray-700 text-xs flex items-center"
                            >
                              <Plus className="w-3 h-3 mr-1" /> Añadir nota
                            </button>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-4">
                        <div className="flex items-center space-x-2">
                          <button
                            onClick={() => toggleLeadSelection(lead.place_id)}
                            className="text-gray-500 hover:text-gray-700"
                            title="Seleccionar"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => {
                              toggleLeadSelection(lead.place_id);
                              setShowLabelsManagement(true);
                            }}
                            className="text-blue-500 hover:text-blue-700"
                            title="Gestionar etiquetas"
                          >
                            <Tag className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => {
                              if (confirm('¿Estás seguro de que quieres eliminar este lead?')) {
                                setSelectedLeads([lead.place_id]);
                                deleteSelectedLeads();
                              }
                            }}
                            className="text-red-500 hover:text-red-700"
                            title="Eliminar"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Añadir el componente de popup para notas */}
      {showNotePopup && addingNoteToId && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium">
                {editingNoteId !== null ? 'Editar Nota' : 'Añadir Nota'}
              </h3>
              <button 
                onClick={cancelEditingNote}
                className="text-gray-500 hover:text-gray-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <textarea
              value={newNote}
              onChange={(e) => setNewNote(e.target.value)}
              placeholder="Escribe tu nota aquí..."
              className="w-full p-3 border border-gray-300 rounded-md min-h-[150px] mb-4"
              autoFocus
            />
            
            <div className="flex justify-end gap-2">
              <button
                onClick={cancelEditingNote}
                className="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
              >
                Cancelar
              </button>
              <button
                onClick={() => addOrUpdateNoteToLead(addingNoteToId)}
                disabled={!newNote.trim()}
                className={`px-4 py-2 rounded-md ${
                  newNote.trim()
                    ? 'bg-blue-600 text-white hover:bg-blue-700'
                    : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                }`}
              >
                {editingNoteId !== null ? 'Actualizar' : 'Guardar'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Añadir modal para gestionar todas las etiquetas */}
      {showLabelsManagement && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-xl">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium">Gestionar Etiquetas</h3>
              <button 
                onClick={() => setShowLabelsManagement(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="mb-6">
              <h4 className="font-medium text-sm text-gray-600 mb-2">Etiquetas predeterminadas</h4>
              <div className="flex flex-wrap gap-2 mb-4">
                {defaultLabels.map(label => (
                  <div 
                    key={label}
                    className="px-3 py-2 bg-gray-100 text-gray-700 rounded-md flex items-center"
                  >
                    {label}
                  </div>
                ))}
              </div>
              
              <h4 className="font-medium text-sm text-gray-600 mb-2">Etiquetas personalizadas</h4>
              <div className="flex flex-wrap gap-2 mb-4">
                {availableLabels.filter(label => !defaultLabels.includes(label)).map(label => (
                  <div 
                    key={label}
                    className="px-3 py-2 bg-blue-50 text-blue-700 rounded-md flex items-center group relative"
                  >
                    {label}
                    <button
                      onClick={() => {
                        if (confirm(`¿Estás seguro de que quieres eliminar la etiqueta "${label}"?`)) {
                          deleteCustomLabel(label);
                        }
                      }}
                      className="ml-2 text-red-500 hover:text-red-700"
                      title="Eliminar etiqueta"
                    >
                      <X className="w-4 h-4" />
                    </button>
                    
                    <button
                      onClick={() => applyLabelsToSelected([label])}
                      className="ml-1 text-green-500 hover:text-green-700" 
                      title="Aplicar a los leads seleccionados"
                    >
                      <Check className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                
                {availableLabels.filter(label => !defaultLabels.includes(label)).length === 0 && (
                  <div className="text-gray-500 text-sm">No hay etiquetas personalizadas.</div>
                )}
              </div>
              
              {showLabelForm ? (
                <div className="flex mb-4">
                  <input
                    type="text"
                    value={newLabelText}
                    onChange={(e) => setNewLabelText(e.target.value)}
                    placeholder="Nueva etiqueta"
                    className="p-2 text-sm border border-gray-300 rounded-l-md flex-grow"
                    autoFocus
                  />
                  <div className="flex">
                    <button
                      onClick={addCustomLabel}
                      disabled={!newLabelText.trim() || savingLabel}
                      className={`px-3 py-2 ${
                        !newLabelText.trim() || savingLabel
                          ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                          : 'bg-green-600 text-white hover:bg-green-700'
                      }`}
                    >
                      {savingLabel ? (
                        <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                      ) : (
                        <Check className="w-4 h-4" />
                      )}
                    </button>
                    <button
                      onClick={() => {
                        setShowLabelForm(false);
                        setNewLabelText('');
                      }}
                      className="px-3 py-2 bg-red-600 text-white hover:bg-red-700 rounded-r-md"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => setShowLabelForm(true)}
                  className="px-3 py-2 bg-blue-600 text-white hover:bg-blue-700 rounded-md flex items-center"
                >
                  <Plus className="w-4 h-4 mr-2" /> Crear nueva etiqueta
                </button>
              )}
            </div>
            
            <div className="flex justify-end">
              <button
                onClick={() => setShowLabelsManagement(false)}
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LeadsPage; 