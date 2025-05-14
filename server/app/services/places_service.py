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
        "radius": min(radius, 50000),  # Google Places API tiene un límite máximo de 50000 metros
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

def search_places_by_type(place_type, location, radius=5000, max_results=20, next_page_token=None, fetch_all=False):
    """
    Buscar lugares según el tipo de negocio/establecimiento y la ubicación, 
    utilizando la API de nearby search que soporta filtro por tipo
    """
    params = {
        "type": place_type,
        "location": location,
        "radius": min(radius, 50000),  # Google Places API tiene un límite máximo de 50000 metros
        "key": API_KEY
    }
    results = []
    token = next_page_token
    fetched = 0
    
    # Variable para evitar bucles infinitos por error de la API
    max_iterations = 10
    iteration = 0
    
    logger.info(f"Iniciando búsqueda por tipo: type={place_type}, location={location}, radius={radius}m")
    
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
            
        response = requests.get(PLACES_NEARBY_URL, params=params)
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
                # La API de nearby search no devuelve la dirección formateada, solo la geometría
                place = {
                    "place_id": place_id,
                    "name": result.get("name"),
                    "address": result.get("vicinity", ""),  # vicinity es similar a formatted_address
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
        
    logger.info(f"Búsqueda por tipo completada. Total de resultados: {len(results)}")
    return results, token

def subdivide_area_search(query, lat, lng, radius, max_results=100, max_depth=2, current_depth=0, callback=None):
    """
    Divide un área grande en cuadrantes más pequeños para obtener más resultados
    utilizando la estrategia de división geográfica recursiva.
    
    Args:
        query: Término de búsqueda
        lat: Latitud del centro
        lng: Longitud del centro
        radius: Radio original en metros
        max_results: Número máximo de resultados a devolver (0 para sin límite)
        max_depth: Profundidad máxima de subdivisión recursiva
        current_depth: Profundidad actual de la recursión
        callback: Función opcional para recibir resultados parciales
        
    Returns:
        Lista de resultados combinados y eliminados duplicados
    """
    depth_str = "  " * current_depth
    logger.info(f"{depth_str}Iniciando búsqueda subdividida (nivel {current_depth}): query={query}, centro=({lat},{lng}), radio={radius}m")
    
    # Asegurarse de que el radio no exceda el límite de la API
    radius = min(radius, 50000)
    
    # Número máximo de resultados a buscar en cada punto antes de considerar que es suficiente
    max_new_results_per_point = 10
    
    # Número máximo de puntos consecutivos con pocos resultados nuevos antes de detenerse
    max_low_yield_points = 5
    low_yield_count = 0
    
    # Definir límites para la profundidad de recursión
    if current_depth >= max_depth:
        num_divisions = 1  # 2x2 = 4 cuadrantes en niveles profundos
    else:
        if radius < 5000:
            num_divisions = 1  # 2x2 = 4 cuadrantes
        elif radius < 20000:
            num_divisions = 2  # 3x3 = 9 cuadrantes
        else:
            num_divisions = 3  # 4x4 = 16 cuadrantes (reducido para evitar exceso de llamadas)
    
    # Factor de reducción de radio para evitar solapamiento excesivo
    radius_factor = 0.7 if current_depth == 0 else 0.8
    sub_radius = radius * radius_factor / (num_divisions + 1)
    
    grid_size = num_divisions * 2 + 1
    logger.info(f"{depth_str}Usando cuadrícula {grid_size}x{grid_size} ({grid_size*grid_size} puntos) con radio {sub_radius}m")
    
    # Calculamos el desplazamiento base en grados
    lat_step = (radius / 111000) / (num_divisions + 0.5)
    lng_step = lat_step / math.cos(math.radians(lat))
    
    # Generar los puntos de la cuadrícula
    grid_points = []
    
    # Crear una cuadrícula de puntos alrededor del centro
    for i in range(-num_divisions, num_divisions+1):
        for j in range(-num_divisions, num_divisions+1):
            grid_points.append({
                "lat": lat + i * lat_step,
                "lng": lng + j * lng_step
            })
    
    logger.info(f"{depth_str}Generados {len(grid_points)} puntos de búsqueda")
    
    all_results = []
    place_ids = set()
    
    # Para cada punto de la cuadrícula
    for i, point in enumerate(grid_points):
        # Si llevamos varios puntos con pocos resultados nuevos, saltar el resto
        if low_yield_count >= max_low_yield_points and current_depth > 0:
            logger.info(f"{depth_str}Saltando puntos restantes debido a bajo rendimiento ({low_yield_count} puntos con pocos resultados nuevos)")
            break
            
        logger.info(f"{depth_str}Buscando en punto {i+1}/{len(grid_points)}: centro=({point['lat']},{point['lng']}), radio={sub_radius}m")
        try:
            # Convertir coordenadas al formato requerido por la API
            location = f"{point['lat']},{point['lng']}"
            
            # Buscar en este punto con el radio correspondiente
            results, _ = search_places(query, location, sub_radius, 60, None, True)
            
            # Agregar resultados no duplicados
            new_results_count = 0
            new_results = []  # Para almacenar solo los resultados nuevos
            
            for result in results:
                place_id = result.get("place_id")
                if place_id and place_id not in place_ids:
                    place_ids.add(place_id)
                    all_results.append(result)
                    new_results.append(result)
                    new_results_count += 1
            
            logger.info(f"{depth_str}Punto {i+1}/{len(grid_points)}: {new_results_count} nuevos resultados, total acumulado: {len(all_results)}")
            
            # Si hay callback y estamos en el nivel principal, enviar resultados parciales
            if callback and current_depth == 0 and new_results:
                callback({
                    "new_results": new_results,
                    "total_count": len(all_results),
                    "status": "in_progress",
                    "progress": {
                        "current_point": i + 1,
                        "total_points": len(grid_points)
                    }
                })
            
            # Evaluar si vale la pena continuar con más puntos
            if new_results_count < max_new_results_per_point:
                low_yield_count += 1
            else:
                low_yield_count = 0  # Reiniciar contador si encontramos suficientes resultados nuevos
            
            # Si estamos en un nivel no demasiado profundo y hemos encontrado muchos resultados,
            # podemos intentar subdividir solo si tiene sentido (pocos puntos con bajo rendimiento)
            if new_results_count >= 20 and current_depth < max_depth and low_yield_count <= 2:
                logger.info(f"{depth_str}Encontrado punto con buenos resultados. Subdividiendo para buscar más.")
                
                # Calcular un radio más pequeño para la subdivisión
                smaller_radius = sub_radius * 0.6
                
                # Llamada recursiva para este punto específico
                sub_results, _ = subdivide_area_search(
                    query, point['lat'], point['lng'], 
                    smaller_radius, max_results,
                    max_depth, current_depth + 1,
                    callback if current_depth == 0 else None  # Solo pasar callback en nivel principal
                )
                
                # Agregar resultados no duplicados de la subdivisión
                sub_new_count = 0
                sub_new_results = []
                
                for result in sub_results:
                    place_id = result.get("place_id")
                    if place_id and place_id not in place_ids:
                        place_ids.add(place_id)
                        all_results.append(result)
                        sub_new_results.append(result)
                        sub_new_count += 1
                
                logger.info(f"{depth_str}Subdivisión añadió {sub_new_count} nuevos resultados, total: {len(all_results)}")
                
                # Si hay callback y estamos en el nivel principal, enviar resultados de subdivisión
                if callback and current_depth == 0 and sub_new_results:
                    callback({
                        "new_results": sub_new_results,
                        "total_count": len(all_results),
                        "status": "in_progress",
                        "progress": {
                            "current_point": i + 1,
                            "total_points": len(grid_points),
                            "subdivision": True
                        }
                    })
            
            # Esperar entre solicitudes para no exceder los límites de la API
            time.sleep(0.5)
            
            # Si ya tenemos suficientes resultados, detenemos la búsqueda
            # Solo si max_results > 0 (si es 0, no hay límite)
            if max_results > 0 and len(all_results) >= max_results and current_depth == 0:
                logger.info(f"{depth_str}Alcanzado máximo de resultados deseados ({max_results}). Deteniendo búsqueda.")
                break
                
        except Exception as e:
            logger.error(f"{depth_str}Error en búsqueda del punto {i+1}: {str(e)}")
    
    logger.info(f"{depth_str}Búsqueda subdividida (nivel {current_depth}) completada. Total de resultados únicos: {len(all_results)}")
    
    # Limitar a max_results si es necesario y no estamos en llamada recursiva
    if current_depth == 0 and max_results > 0 and len(all_results) > max_results:
        logger.info(f"{depth_str}Limitando resultados a {max_results} (de {len(all_results)} encontrados)")
        all_results = all_results[:max_results]
    
    # Si hay callback y hemos terminado la búsqueda principal, enviar evento de finalización
    if callback and current_depth == 0:
        callback({
            "new_results": [],
            "total_count": len(all_results),
            "status": "completed",
            "progress": {
                "current_point": len(grid_points),
                "total_points": len(grid_points)
            }
        })
        
    return all_results, None  # No hay token de paginación en búsquedas subdivididas

def subdivide_area_search_by_type(place_type, lat, lng, radius, max_results=100, max_depth=2, current_depth=0, callback=None):
    """
    Divide un área grande en cuadrantes más pequeños para obtener más resultados
    cuando se busca por tipo de establecimiento, usando estrategia recursiva.
    
    Args:
        place_type: Tipo de establecimiento a buscar
        lat: Latitud del centro
        lng: Longitud del centro
        radius: Radio original en metros
        max_results: Número máximo de resultados a devolver (0 para sin límite)
        max_depth: Profundidad máxima de subdivisión recursiva
        current_depth: Profundidad actual de la recursión
        callback: Función opcional para recibir resultados parciales
    """
    depth_str = "  " * current_depth
    logger.info(f"{depth_str}Iniciando búsqueda por tipo subdividida (nivel {current_depth}): type={place_type}, centro=({lat},{lng}), radio={radius}m")
    
    # Asegurarse de que el radio no exceda el límite de la API
    radius = min(radius, 50000)
    
    # Número máximo de resultados a buscar en cada punto antes de considerar que es suficiente
    max_new_results_per_point = 10
    
    # Número máximo de puntos consecutivos con pocos resultados nuevos antes de detenerse
    max_low_yield_points = 5
    low_yield_count = 0
    
    # Definir límites para la profundidad de recursión
    if current_depth >= max_depth:
        num_divisions = 1  # 2x2 = 4 cuadrantes en niveles profundos
    else:
        if radius < 5000:
            num_divisions = 1  # 2x2 = 4 cuadrantes
        elif radius < 20000:
            num_divisions = 2  # 3x3 = 9 cuadrantes
        else:
            num_divisions = 3  # 4x4 = 16 cuadrantes (reducido para evitar exceso de llamadas)
    
    # Factor de reducción de radio para evitar solapamiento excesivo
    radius_factor = 0.7 if current_depth == 0 else 0.8
    sub_radius = radius * radius_factor / (num_divisions + 1)
    
    grid_size = num_divisions * 2 + 1
    logger.info(f"{depth_str}Usando cuadrícula {grid_size}x{grid_size} ({grid_size*grid_size} puntos) con radio {sub_radius}m")
    
    # Calculamos el desplazamiento base en grados
    lat_step = (radius / 111000) / (num_divisions + 0.5)
    lng_step = lat_step / math.cos(math.radians(lat))
    
    # Generar los puntos de la cuadrícula
    grid_points = []
    
    # Crear una cuadrícula de puntos alrededor del centro
    for i in range(-num_divisions, num_divisions+1):
        for j in range(-num_divisions, num_divisions+1):
            grid_points.append({
                "lat": lat + i * lat_step,
                "lng": lng + j * lng_step
            })
    
    logger.info(f"{depth_str}Generados {len(grid_points)} puntos de búsqueda para tipo {place_type}")
    
    all_results = []
    place_ids = set()
    
    # Para cada punto de la cuadrícula
    for i, point in enumerate(grid_points):
        # Si llevamos varios puntos con pocos resultados nuevos, saltar el resto
        if low_yield_count >= max_low_yield_points and current_depth > 0:
            logger.info(f"{depth_str}Saltando puntos restantes debido a bajo rendimiento ({low_yield_count} puntos con pocos resultados nuevos)")
            break
            
        logger.info(f"{depth_str}Buscando en punto {i+1}/{len(grid_points)}: centro=({point['lat']},{point['lng']}), radio={sub_radius}m")
        try:
            # Convertir coordenadas al formato requerido por la API
            location = f"{point['lat']},{point['lng']}"
            
            # Buscar en este punto con el radio correspondiente
            results, _ = search_places_by_type(place_type, location, sub_radius, 60, None, True)
            
            # Agregar resultados no duplicados
            new_results_count = 0
            new_results = []  # Para almacenar solo los resultados nuevos
            
            for result in results:
                place_id = result.get("place_id")
                if place_id and place_id not in place_ids:
                    place_ids.add(place_id)
                    all_results.append(result)
                    new_results.append(result)
                    new_results_count += 1
            
            logger.info(f"{depth_str}Punto {i+1}/{len(grid_points)}: {new_results_count} nuevos resultados, total acumulado: {len(all_results)}")
            
            # Si hay callback y estamos en el nivel principal, enviar resultados parciales
            if callback and current_depth == 0 and new_results:
                callback({
                    "new_results": new_results,
                    "total_count": len(all_results),
                    "status": "in_progress",
                    "progress": {
                        "current_point": i + 1,
                        "total_points": len(grid_points)
                    }
                })
            
            # Evaluar si vale la pena continuar con más puntos
            if new_results_count < max_new_results_per_point:
                low_yield_count += 1
            else:
                low_yield_count = 0  # Reiniciar contador si encontramos suficientes resultados nuevos
            
            # Si estamos en un nivel no demasiado profundo y hemos encontrado muchos resultados,
            # podemos intentar subdividir solo si tiene sentido (pocos puntos con bajo rendimiento)
            if new_results_count >= 20 and current_depth < max_depth and low_yield_count <= 2:
                logger.info(f"{depth_str}Encontrado punto con buenos resultados. Subdividiendo para buscar más.")
                
                # Calcular un radio más pequeño para la subdivisión
                smaller_radius = sub_radius * 0.6
                
                # Llamada recursiva para este punto específico
                sub_results, _ = subdivide_area_search_by_type(
                    place_type, point['lat'], point['lng'], 
                    smaller_radius, max_results,
                    max_depth, current_depth + 1,
                    callback if current_depth == 0 else None  # Solo pasar callback en nivel principal
                )
                
                # Agregar resultados no duplicados de la subdivisión
                sub_new_count = 0
                sub_new_results = []
                
                for result in sub_results:
                    place_id = result.get("place_id")
                    if place_id and place_id not in place_ids:
                        place_ids.add(place_id)
                        all_results.append(result)
                        sub_new_results.append(result)
                        sub_new_count += 1
                
                logger.info(f"{depth_str}Subdivisión añadió {sub_new_count} nuevos resultados, total: {len(all_results)}")
                
                # Si hay callback y estamos en el nivel principal, enviar resultados de subdivisión
                if callback and current_depth == 0 and sub_new_results:
                    callback({
                        "new_results": sub_new_results,
                        "total_count": len(all_results),
                        "status": "in_progress",
                        "progress": {
                            "current_point": i + 1,
                            "total_points": len(grid_points),
                            "subdivision": True
                        }
                    })
            
            # Esperar entre solicitudes para no exceder los límites de la API
            time.sleep(0.5)
            
            # Si ya tenemos suficientes resultados, detenemos la búsqueda
            # Solo si max_results > 0 (si es 0, no hay límite)
            if max_results > 0 and len(all_results) >= max_results and current_depth == 0:
                logger.info(f"{depth_str}Alcanzado máximo de resultados deseados ({max_results}). Deteniendo búsqueda.")
                break
                
        except Exception as e:
            logger.error(f"{depth_str}Error en búsqueda del punto {i+1}: {str(e)}")
    
    logger.info(f"{depth_str}Búsqueda por tipo subdividida (nivel {current_depth}) completada. Total de resultados únicos: {len(all_results)}")
    
    # Limitar a max_results si es necesario y no estamos en llamada recursiva
    if current_depth == 0 and max_results > 0 and len(all_results) > max_results:
        logger.info(f"{depth_str}Limitando resultados a {max_results} (de {len(all_results)} encontrados)")
        all_results = all_results[:max_results]
    
    # Si hay callback y hemos terminado la búsqueda principal, enviar evento de finalización
    if callback and current_depth == 0:
        callback({
            "new_results": [],
            "total_count": len(all_results),
            "status": "completed",
            "progress": {
                "current_point": len(grid_points),
                "total_points": len(grid_points)
            }
        })
        
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

# URL para autocompletado de Google Places
PLACES_AUTOCOMPLETE_URL = "https://maps.googleapis.com/maps/api/place/autocomplete/json"

def get_place_autocomplete(input_text, location=None, radius=None, types=None):
    """
    Obtener sugerencias de autocompletado para lugares a partir de un texto parcial.
    
    Args:
        input_text: El texto parcial para buscar sugerencias
        location: Opcional. Coordenadas de ubicación para influir en los resultados (format: "lat,lng")
        radius: Opcional. Radio en metros para buscar alrededor de la ubicación
        types: Opcional. Limitar resultados a ciertos tipos de lugares (business, address, etc.)
        
    Returns:
        Lista de predicciones de lugares con description y place_id
    """
    logger.info(f"Obteniendo autocompletado para: '{input_text}'")
    
    params = {
        "input": input_text,
        "key": API_KEY,
    }
    
    # Añadir parámetros opcionales si están disponibles
    if location:
        params["location"] = location
    
    if radius:
        params["radius"] = radius
    
    if types:
        params["types"] = types
    
    try:
        response = requests.get(PLACES_AUTOCOMPLETE_URL, params=params)
        data = response.json()
        
        if data.get("status") not in ["OK", "ZERO_RESULTS"]:
            error_message = data.get("error_message", "Error desconocido en la API de Google Places")
            logger.error(f"Error en autocompletado: {error_message}")
            raise Exception(f"Error en la API de Google Places: {error_message}")
        
        predictions = data.get("predictions", [])
        logger.info(f"Se encontraron {len(predictions)} sugerencias para '{input_text}'")
        
        # Transformar y limpiar las predicciones
        result = []
        for prediction in predictions:
            result.append({
                "place_id": prediction.get("place_id"),
                "description": prediction.get("description"),
                "types": prediction.get("types", []),
                "terms": [term.get("value") for term in prediction.get("terms", [])]
            })
        
        return result
    except Exception as e:
        logger.exception(f"Error al obtener autocompletado: {str(e)}")
        return []

# URL para búsqueda de texto de Query Autocomplete
PLACES_QUERY_AUTOCOMPLETE_URL = "https://maps.googleapis.com/maps/api/place/queryautocomplete/json"

def get_query_autocomplete(input_text, location=None, radius=None):
    """
    Obtener sugerencias de autocompletado para consultas de búsqueda (incluye negocios, categorías, etc.)
    
    Args:
        input_text: El texto parcial para buscar sugerencias
        location: Opcional. Coordenadas de ubicación para influir en los resultados (format: "lat,lng")
        radius: Opcional. Radio en metros para buscar alrededor de la ubicación
        
    Returns:
        Lista de predicciones con description y tipos
    """
    logger.info(f"Obteniendo autocompletado de consulta para: '{input_text}'")
    
    params = {
        "input": input_text,
        "key": API_KEY,
    }
    
    # Añadir parámetros opcionales si están disponibles
    if location:
        params["location"] = location
    
    if radius:
        params["radius"] = radius
    
    try:
        response = requests.get(PLACES_QUERY_AUTOCOMPLETE_URL, params=params)
        data = response.json()
        
        if data.get("status") not in ["OK", "ZERO_RESULTS"]:
            error_message = data.get("error_message", "Error desconocido en la API de Google Places")
            logger.error(f"Error en autocompletado de consulta: {error_message}")
            raise Exception(f"Error en la API de Google Places: {error_message}")
        
        predictions = data.get("predictions", [])
        logger.info(f"Se encontraron {len(predictions)} sugerencias de consulta para '{input_text}'")
        
        # Transformar y limpiar las predicciones
        result = []
        for prediction in predictions:
            result.append({
                "description": prediction.get("description"),
                "place_id": prediction.get("place_id", ""),
                "types": prediction.get("types", []),
                "terms": [term.get("value") for term in prediction.get("terms", [])]
            })
        
        return result
    except Exception as e:
        logger.exception(f"Error al obtener autocompletado de consulta: {str(e)}")
        return [] 