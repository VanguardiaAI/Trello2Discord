import requests
import os
import time
import logging
from dotenv import load_dotenv

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
    while True:
        if token:
            params["pagetoken"] = token
            # Google recomienda esperar 2 segundos antes de usar el next_page_token
            time.sleep(2)
        else:
            params.pop("pagetoken", None)
        response = requests.get(PLACES_SEARCH_URL, params=params)
        data = response.json()
        if data.get("status") not in ["OK", "ZERO_RESULTS"]:
            error_message = data.get("error_message", "Error desconocido en la API de Google Places")
            raise Exception(f"Error en la API de Google Places: {error_message}")
        for result in data.get("results", []):
            place = {
                "place_id": result.get("place_id"),
                "name": result.get("name"),
                "address": result.get("formatted_address"),
                "rating": result.get("rating"),
                "location": result.get("geometry", {}).get("location")
            }
            results.append(place)
            fetched += 1
            if not fetch_all and fetched >= max_results:
                break
        # Si no hay más resultados o alcanzamos el máximo
        token = data.get("next_page_token")
        if not token or (not fetch_all and fetched >= max_results):
            break
    # Limitar resultados si no es fetch_all
    if not fetch_all:
        results = results[:max_results]
    return results, token

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