import requests
import os
import time
import logging
from dotenv import load_dotenv
import math

# Configurar logger
logger = logging.getLogger(__name__)

# Cargar variables de entorno si no están cargadas
load_dotenv()

# Obtener la clave de API de Google Places
API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")
if not API_KEY:
    raise ValueError("La API KEY de Google Places no está configurada en el archivo .env")

# URLs de la API
PLACES_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACES_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
PLACES_NEARBY_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

def search_places(query, location, radius=5000, max_results=20, next_page_token=None, fetch_all=False):
    """
    Buscar lugares según el query y la ubicación, soportando paginación y cantidad máxima
    """
    params = {
        "query": query,
        "location": location,
        "radius": radius,
        "key": API_KEY
    }
    results = []
    token = next_page_token
    fetched = 0
    
    # Variable para evitar bucles infinitos por error de la API
    max_iterations = 10
    iteration = 0
    
    logger.info(f"Iniciando búsqueda: query={query}, location={location}, radius={radius}m")
    
    while True:
        iteration += 1
        if iteration > max_iterations:
            logger.warning(f"Se alcanzó el máximo de iteraciones ({max_iterations}). Terminando búsqueda.")
            break
            
        if token:
            params["pagetoken"] = token
            # Google recomienda esperar antes de usar el next_page_token
            time.sleep(2)
            logger.info(f"Usando token de paginación para obtener más resultados")
        else:
            params.pop("pagetoken", None)
            
        response = requests.get(PLACES_SEARCH_URL, params=params)
        data = response.json()
        
        if data.get("status") not in ["OK", "ZERO_RESULTS"]:
            error_message = data.get("error_message", "Error desconocido en la API de Google Places")
            logger.error(f"Error en API: {error_message}")
            raise Exception(f"Error en la API de Google Places: {error_message}")
            
        # Verificar si hay resultados en esta página
        page_results = data.get("results", [])
        new_results_count = len(page_results)
        logger.info(f"Se encontraron {new_results_count} lugares en esta página")
        
        for result in page_results:
            # Verificar si el resultado ya existe en nuestra lista por place_id
            place_id = result.get("place_id")
            if not any(r.get("place_id") == place_id for r in results):
                place = {
                    "place_id": place_id,
                    "name": result.get("name"),
                    "address": result.get("formatted_address"),
                    "rating": result.get("rating"),
                    "location": result.get("geometry", {}).get("location")
                }
                results.append(place)
                fetched += 1
            
            if not fetch_all and fetched >= max_results:
                logger.info(f"Se alcanzó el máximo de resultados solicitados: {max_results}")
                break
                
        # Si no hay más resultados o alcanzamos el máximo
        token = data.get("next_page_token")
        if not token:
            logger.info("No hay más páginas de resultados disponibles")
            break
            
        if not fetch_all and fetched >= max_results:
            logger.info(f"Se alcanzó el máximo de resultados solicitados: {max_results}")
            break
    
    # Limitar resultados si no es fetch_all
    if not fetch_all and len(results) > max_results:
        results = results[:max_results]
        
    logger.info(f"Búsqueda completada. Total de resultados: {len(results)}")
    return results, token

def subdivide_area_search(query, lat, lng, radius, max_results=100):
    """
    Divide un área grande en cuadrantes más pequeños para obtener más resultados
    utilizando la estrategia de división geográfica.
    
    Args:
        query: Término de búsqueda
        lat: Latitud del centro
        lng: Longitud del centro
        radius: Radio original en metros
        max_results: Número máximo de resultados a devolver
        
    Returns:
        Lista de resultados combinados y eliminados duplicados
    """
    logger.info(f"Iniciando búsqueda subdividida para: query={query}, centro=({lat},{lng}), radio={radius}m")
    
    # Determinar tamaño de los subradios (dividimos el radio original entre 2)
    sub_radius = radius / 2
    
    # Calculamos cuánto desplazarnos desde el centro para crear 4 cuadrantes
    # que cubran toda el área con cierta superposición
    offset = sub_radius * 0.7  # 70% del subradio para garantizar superposición
    
    # Definimos los centros de los 4 cuadrantes
    quadrants = [
        {"lat": lat + offset/111000, "lng": lng + offset/(111000*math.cos(math.radians(lat)))},  # Noreste
        {"lat": lat + offset/111000, "lng": lng - offset/(111000*math.cos(math.radians(lat)))},  # Noroeste
        {"lat": lat - offset/111000, "lng": lng + offset/(111000*math.cos(math.radians(lat)))},  # Sureste
        {"lat": lat - offset/111000, "lng": lng - offset/(111000*math.cos(math.radians(lat)))},  # Suroeste
    ]
    
    all_results = []
    place_ids = set()
    
    # Realizar búsqueda en cada cuadrante
    for i, quad in enumerate(quadrants):
        logger.info(f"Buscando en cuadrante {i+1}/4: centro=({quad['lat']},{quad['lng']}), radio={sub_radius}m")
        try:
            # Convertir coordenadas al formato requerido por la API
            location = f"{quad['lat']},{quad['lng']}"
            
            # Buscar en este cuadrante
            results, _ = search_places(query, location, sub_radius, max_results, None, True)
            
            # Agregar resultados no duplicados
            for result in results:
                place_id = result.get("place_id")
                if place_id and place_id not in place_ids:
                    place_ids.add(place_id)
                    all_results.append(result)
            
            logger.info(f"Cuadrante {i+1}/4 completado. Resultados acumulados: {len(all_results)}")
            
            # Esperar entre solicitudes para no exceder los límites de la API
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error en búsqueda del cuadrante {i+1}: {str(e)}")
    
    logger.info(f"Búsqueda subdividida completada. Total de resultados únicos: {len(all_results)}")
    
    # Limitar a max_results si es necesario
    if len(all_results) > max_results:
        all_results = all_results[:max_results]
        
    return all_results, None  # No hay token de paginación en búsquedas subdivididas

def get_place_details(place_id):
    """
    Obtener detalles completos de un lugar a partir de su place_id
    """
    logger.info(f"Obteniendo detalles para place_id: {place_id}")
    
    params = {
        "place_id": place_id,
        "fields": "place_id,name,formatted_address,formatted_phone_number,website,rating,url",
        "key": API_KEY
    }
    
    try:
        response = requests.get(PLACES_DETAILS_URL, params=params)
        data = response.json()
        
        if data.get("status") != "OK":
            error_message = data.get("error_message", "Error desconocido en la API de Google Places")
            logger.error(f"Error API Google Places: {error_message}")
            raise Exception(f"Error en la API de Google Places: {error_message}")
        
        # Asegurarse de que el resultado tiene el place_id
        result = data.get("result", {})
        
        # Si no incluye el place_id en los resultados, lo agregamos manualmente
        if "place_id" not in result:
            result["place_id"] = place_id
            
        logger.info(f"Detalles obtenidos para {place_id}: {result.get('name')}")
        
        return result
    except Exception as e:
        logger.exception(f"Error al obtener detalles del lugar: {str(e)}")
        # En caso de error, devolvemos al menos un objeto con el place_id
        return {"place_id": place_id, "name": "Error al obtener detalles"} 