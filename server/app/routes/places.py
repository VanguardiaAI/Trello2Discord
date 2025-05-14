from flask import Blueprint, request, jsonify, current_app, Response, stream_with_context
from app.services.places_service import search_places, get_place_details, subdivide_area_search, search_places_by_type, subdivide_area_search_by_type, get_place_autocomplete, get_query_autocomplete
from app.services.geocoding_service import geocode_address
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import logging
import unicodedata
import json
import time
from threading import Thread

places_bp = Blueprint('places', __name__)

# Configurar logger
logger = logging.getLogger(__name__)

# Definir si queremos autenticación obligatoria o no (para desarrollo)
REQUIRE_AUTH = os.environ.get('REQUIRE_AUTH', 'false').lower() == 'true'

# Decorador personalizado para hacer jwt_required opcional según la configuración
def auth_optional(fn):
    if REQUIRE_AUTH:
        return jwt_required()(fn)
    return fn

@places_bp.route("/geocode", methods=["GET"])
@auth_optional
def geocode():
    address = request.args.get('address')
    if not address:
        return jsonify({"error": "Se requiere el parámetro 'address'"}), 400
    try:
        result = geocode_address(address)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@places_bp.route("/places/search", methods=["GET"])
@auth_optional
def search():
    """Buscar places en Google Places API según nicho y área"""
    query = request.args.get('query')
    address = request.args.get('address')
    radius = request.args.get('radius', 5000, type=int)
    max_results = request.args.get('max_results', 20, type=int)
    next_page_token = request.args.get('next_page_token')
    fetch_all = request.args.get('fetch_all', 'false').lower() == 'true'
    
    if not query or not address:
        return jsonify({"error": "Se requieren los parámetros 'query' y 'address'"}), 400
    
    try:
        # Geocodificar la dirección
        geo = geocode_address(address)
        latlng = f"{geo['lat']},{geo['lng']}"
        
        # Si hay token de paginación, continuamos la búsqueda anterior
        if next_page_token:
            logger.info(f"Continuando búsqueda con token de paginación")
            results, next_token = search_places(query, latlng, radius, max_results, next_page_token, fetch_all)
        else:
            # Si no hay token, es una nueva búsqueda
            logger.info(f"Iniciando nueva búsqueda: {query} en {address} con radio {radius}m")
            results, next_token = search_places(query, latlng, radius, max_results, None, fetch_all)
        
        return jsonify({
            "results": results,
            "next_page_token": next_token
        })
    except Exception as e:
        logger.error(f"Error en búsqueda: {str(e)}")
        return jsonify({"error": str(e)}), 500

@places_bp.route("/places/search/by-type", methods=["GET"])
@auth_optional
def search_by_type():
    """Buscar places por tipo de establecimiento"""
    place_type = request.args.get('type')
    address = request.args.get('address')
    radius = request.args.get('radius', 5000, type=int)
    max_results = request.args.get('max_results', 20, type=int)
    next_page_token = request.args.get('next_page_token')
    fetch_all = request.args.get('fetch_all', 'false').lower() == 'true'
    
    if not place_type or not address:
        return jsonify({"error": "Se requieren los parámetros 'type' y 'address'"}), 400
    
    try:
        # Geocodificar la dirección
        geo = geocode_address(address)
        latlng = f"{geo['lat']},{geo['lng']}"
        
        # Si hay token de paginación, continuamos la búsqueda anterior
        if next_page_token:
            logger.info(f"Continuando búsqueda por tipo con token de paginación")
            results, next_token = search_places_by_type(place_type, latlng, radius, max_results, next_page_token, fetch_all)
        else:
            # Si no hay token, es una nueva búsqueda
            logger.info(f"Iniciando nueva búsqueda por tipo: {place_type} en {address} con radio {radius}m")
            results, next_token = search_places_by_type(place_type, latlng, radius, max_results, None, fetch_all)
        
        return jsonify({
            "results": results,
            "next_page_token": next_token,
            "type": place_type
        })
    except Exception as e:
        logger.error(f"Error en búsqueda por tipo: {str(e)}")
        return jsonify({"error": str(e)}), 500

@places_bp.route("/places/search/subdivide", methods=["GET"])
@auth_optional
def search_subdivided():
    """Buscar places utilizando la estrategia de subdivisión de área para obtener más resultados"""
    query = request.args.get('query')
    address = request.args.get('address')
    radius = request.args.get('radius', 5000, type=int)
    max_results = request.args.get('max_results', 100, type=int)
    
    if not query or not address:
        return jsonify({"error": "Se requieren los parámetros 'query' y 'address'"}), 400
    
    try:
        # Geocodificar la dirección
        geo = geocode_address(address)
        
        logger.info(f"Iniciando búsqueda subdividida: {query} en {address} con radio {radius}m")
        
        # Realizar búsqueda subdividida
        results, _ = subdivide_area_search(query, geo['lat'], geo['lng'], radius, max_results)
        
        return jsonify({
            "results": results,
            "next_page_token": None,  # No hay paginación en búsquedas subdivididas
            "subdivided": True,
            "total_results": len(results)
        })
    except Exception as e:
        logger.error(f"Error en búsqueda subdividida: {str(e)}")
        return jsonify({"error": str(e)}), 500

@places_bp.route("/places/search/by-type/subdivide", methods=["GET"])
@auth_optional
def search_by_type_subdivided():
    """Buscar places por tipo utilizando la estrategia de subdivisión de área"""
    place_type = request.args.get('type')
    address = request.args.get('address')
    radius = request.args.get('radius', 5000, type=int)
    max_results = request.args.get('max_results', 100, type=int)
    
    if not place_type or not address:
        return jsonify({"error": "Se requieren los parámetros 'type' y 'address'"}), 400
    
    try:
        # Geocodificar la dirección
        geo = geocode_address(address)
        
        logger.info(f"Iniciando búsqueda por tipo subdividida: {place_type} en {address} con radio {radius}m")
        
        # Realizar búsqueda subdividida
        results, _ = subdivide_area_search_by_type(place_type, geo['lat'], geo['lng'], radius, max_results)
        
        return jsonify({
            "results": results,
            "next_page_token": None,  # No hay paginación en búsquedas subdivididas
            "subdivided": True,
            "type": place_type,
            "total_results": len(results)
        })
    except Exception as e:
        logger.error(f"Error en búsqueda por tipo subdividida: {str(e)}")
        return jsonify({"error": str(e)}), 500

@places_bp.route("/places/search/full", methods=["GET"])
@auth_optional
def search_full():
    """Buscar todos los lugares posibles combinando múltiples estrategias"""
    query = request.args.get('query')
    address = request.args.get('address')
    radius = request.args.get('radius', 5000, type=int)
    max_results = request.args.get('max_results', 500, type=int)
    
    if not query or not address:
        return jsonify({"error": "Se requieren los parámetros 'query' y 'address'"}), 400
    
    try:
        # Geocodificar la dirección
        geo = geocode_address(address)
        latlng = f"{geo['lat']},{geo['lng']}"
        
        # Aplicar límite de radio
        original_radius = radius
        radius = min(radius, 50000)
        
        if original_radius != radius:
            logger.info(f"Ajustando radio de búsqueda de {original_radius}m a {radius}m (límite de API)")
        
        logger.info(f"BÚSQUEDA COMPLETA MASIVA INICIADA: '{query}' en {address} con radio={radius}m")
        
        # 1. Primero hacemos una búsqueda normal con fetch_all=True
        logger.info(f"Paso 1 - Búsqueda estándar con radio {radius}m para '{query}'")
        standard_results, _ = search_places(query, latlng, radius, 60, None, True)
        logger.info(f"Paso 1 completado: {len(standard_results)} resultados encontrados con búsqueda estándar")
        
        # 2. Luego hacemos búsqueda subdividida recursiva 
        logger.info(f"Paso 2 - Búsqueda subdividida avanzada con radio {radius}m para '{query}'")
        
        # Determinar profundidad máxima de recursión según el radio
        # Para radios grandes usamos más niveles de recursión
        max_depth = 2  # Valor por defecto
        
        if radius < 5000:
            max_depth = 1  # Menos divisiones para radios pequeños
        elif radius > 25000:
            max_depth = 3  # Más divisiones para radios grandes
            
        logger.info(f"Usando profundidad máxima de recursión: {max_depth} para radio {radius}m")
        
        # Llamar a la función de búsqueda subdividida con recursión
        subdivided_results, _ = subdivide_area_search(
            query, geo['lat'], geo['lng'], radius, max_results, max_depth
        )
        
        logger.info(f"Paso 2 completado: {len(subdivided_results)} resultados encontrados con búsqueda subdividida avanzada")
        
        # Combinar resultados y eliminar duplicados
        all_results = []
        place_ids = set()
        
        # Procesar resultados estándar
        standard_count = 0
        for result in standard_results:
            place_id = result.get("place_id")
            if place_id and place_id not in place_ids:
                place_ids.add(place_id)
                all_results.append(result)
                standard_count += 1
                
        logger.info(f"Añadidos {standard_count} resultados únicos de la búsqueda estándar")
                
        # Procesar resultados de búsqueda subdividida
        duplicados = 0
        nuevos = 0
        for result in subdivided_results:
            place_id = result.get("place_id")
            if place_id and place_id not in place_ids:
                place_ids.add(place_id)
                all_results.append(result)
                nuevos += 1
            else:
                duplicados += 1
        
        logger.info(f"Combinación de resultados: {nuevos} nuevos lugares añadidos de la búsqueda subdividida, {duplicados} duplicados omitidos")
        logger.info(f"BÚSQUEDA COMPLETA MASIVA FINALIZADA: '{query}' - Total {len(all_results)} resultados únicos")
        
        # Limitar resultados finales si exceden el máximo solicitado
        if len(all_results) > max_results:
            logger.info(f"Limitando resultados a {max_results} (de {len(all_results)} encontrados)")
            all_results = all_results[:max_results]
        
        return jsonify({
            "results": all_results,
            "next_page_token": None,
            "full_search": True,
            "total_results": len(all_results),
            "standard_results": len(standard_results),
            "subdivided_results": len(subdivided_results),
            "nuevos_de_subdivision": nuevos,
            "radio_usado": radius,
            "radio_solicitado": original_radius,
            "max_depth_usado": max_depth
        })
    except Exception as e:
        logger.error(f"Error en búsqueda completa: {str(e)}")
        return jsonify({"error": str(e)}), 500

@places_bp.route("/places/search/by-type/full", methods=["GET"])
@auth_optional
def search_by_type_full():
    """Buscar todos los lugares posibles por tipo combinando múltiples estrategias"""
    place_type = request.args.get('type')
    address = request.args.get('address')
    radius = request.args.get('radius', 5000, type=int)
    max_results = request.args.get('max_results', 500, type=int)
    
    if not place_type or not address:
        return jsonify({"error": "Se requieren los parámetros 'type' y 'address'"}), 400
    
    try:
        # Geocodificar la dirección
        geo = geocode_address(address)
        latlng = f"{geo['lat']},{geo['lng']}"
        
        # Aplicar límite de radio
        original_radius = radius
        radius = min(radius, 50000)
        
        if original_radius != radius:
            logger.info(f"Ajustando radio de búsqueda de {original_radius}m a {radius}m (límite de API)")
        
        logger.info(f"BÚSQUEDA COMPLETA POR TIPO INICIADA: '{place_type}' en {address} con radio={radius}m")
        
        # 1. Primero hacemos una búsqueda normal con fetch_all=True
        logger.info(f"Paso 1 - Búsqueda estándar por tipo con radio {radius}m para '{place_type}'")
        standard_results, _ = search_places_by_type(place_type, latlng, radius, 60, None, True)
        logger.info(f"Paso 1 completado: {len(standard_results)} resultados encontrados con búsqueda estándar por tipo")
        
        # 2. Luego hacemos búsqueda subdividida recursiva
        logger.info(f"Paso 2 - Búsqueda subdividida avanzada por tipo con radio {radius}m para '{place_type}'")
        
        # Determinar profundidad máxima de recursión según el radio
        # Para radios grandes usamos más niveles de recursión
        max_depth = 2  # Valor por defecto
        
        if radius < 5000:
            max_depth = 1  # Menos divisiones para radios pequeños
        elif radius > 25000:
            max_depth = 3  # Más divisiones para radios grandes
            
        logger.info(f"Usando profundidad máxima de recursión: {max_depth} para radio {radius}m")
        
        # Llamar a la función de búsqueda subdividida con recursión
        subdivided_results, _ = subdivide_area_search_by_type(
            place_type, geo['lat'], geo['lng'], radius, max_results, max_depth
        )
        
        logger.info(f"Paso 2 completado: {len(subdivided_results)} resultados encontrados con búsqueda subdividida avanzada por tipo")
        
        # Combinar resultados y eliminar duplicados
        all_results = []
        place_ids = set()
        
        # Procesar resultados estándar
        standard_count = 0
        for result in standard_results:
            place_id = result.get("place_id")
            if place_id and place_id not in place_ids:
                place_ids.add(place_id)
                all_results.append(result)
                standard_count += 1
                
        logger.info(f"Añadidos {standard_count} resultados únicos de la búsqueda estándar por tipo")
                
        # Procesar resultados de búsqueda subdividida
        duplicados = 0
        nuevos = 0
        for result in subdivided_results:
            place_id = result.get("place_id")
            if place_id and place_id not in place_ids:
                place_ids.add(place_id)
                all_results.append(result)
                nuevos += 1
            else:
                duplicados += 1
        
        logger.info(f"Combinación de resultados: {nuevos} nuevos lugares añadidos de la búsqueda subdividida por tipo, {duplicados} duplicados omitidos")
        logger.info(f"BÚSQUEDA COMPLETA POR TIPO FINALIZADA: '{place_type}' - Total {len(all_results)} resultados únicos")
        
        # Limitar resultados finales si exceden el máximo solicitado
        if len(all_results) > max_results:
            logger.info(f"Limitando resultados a {max_results} (de {len(all_results)} encontrados)")
            all_results = all_results[:max_results]
        
        return jsonify({
            "results": all_results,
            "next_page_token": None,
            "full_search": True,
            "type": place_type,
            "total_results": len(all_results),
            "standard_results": len(standard_results),
            "subdivided_results": len(subdivided_results),
            "nuevos_de_subdivision": nuevos,
            "radio_usado": radius,
            "radio_solicitado": original_radius,
            "max_depth_usado": max_depth
        })
    except Exception as e:
        logger.error(f"Error en búsqueda completa por tipo: {str(e)}")
        return jsonify({"error": str(e)}), 500

@places_bp.route("/places/types", methods=["GET"])
@auth_optional
def get_place_types():
    """Obtener los tipos de lugares disponibles en Google Places API"""
    # Lista de tipos principales de lugares según la documentación de Google Places API
    place_types = [
        {
            "id": "accounting",
            "name": "Contabilidad",
            "category": "Servicios Profesionales"
        },
        {
            "id": "airport",
            "name": "Aeropuerto",
            "category": "Transporte"
        },
        {
            "id": "amusement_park",
            "name": "Parque de diversiones",
            "category": "Entretenimiento"
        },
        {
            "id": "aquarium",
            "name": "Acuario",
            "category": "Entretenimiento"
        },
        {
            "id": "art_gallery",
            "name": "Galería de arte",
            "category": "Arte y Cultura"
        },
        {
            "id": "atm",
            "name": "Cajero automático",
            "category": "Servicios Financieros"
        },
        {
            "id": "bakery",
            "name": "Panadería",
            "category": "Alimentación"
        },
        {
            "id": "bank",
            "name": "Banco",
            "category": "Servicios Financieros"
        },
        {
            "id": "bar",
            "name": "Bar",
            "category": "Gastronomía"
        },
        {
            "id": "beauty_salon",
            "name": "Salón de belleza",
            "category": "Belleza y Spa"
        },
        {
            "id": "bicycle_store",
            "name": "Tienda de bicicletas",
            "category": "Comercio"
        },
        {
            "id": "book_store",
            "name": "Librería",
            "category": "Comercio"
        },
        {
            "id": "car_dealer",
            "name": "Concesionario de coches",
            "category": "Automoción"
        },
        {
            "id": "car_rental",
            "name": "Alquiler de coches",
            "category": "Automoción"
        },
        {
            "id": "car_repair",
            "name": "Taller mecánico",
            "category": "Automoción"
        },
        {
            "id": "car_wash",
            "name": "Lavadero de coches",
            "category": "Automoción"
        },
        {
            "id": "casino",
            "name": "Casino",
            "category": "Entretenimiento"
        },
        {
            "id": "cemetery",
            "name": "Cementerio",
            "category": "Servicios"
        },
        {
            "id": "church",
            "name": "Iglesia",
            "category": "Religión"
        },
        {
            "id": "city_hall",
            "name": "Ayuntamiento",
            "category": "Administración Pública"
        },
        {
            "id": "clothing_store",
            "name": "Tienda de ropa",
            "category": "Comercio"
        },
        {
            "id": "convenience_store",
            "name": "Tienda de conveniencia",
            "category": "Comercio"
        },
        {
            "id": "dentist",
            "name": "Dentista",
            "category": "Salud"
        },
        {
            "id": "department_store",
            "name": "Gran almacén",
            "category": "Comercio"
        },
        {
            "id": "doctor",
            "name": "Médico",
            "category": "Salud"
        },
        {
            "id": "electrician",
            "name": "Electricista",
            "category": "Servicios"
        },
        {
            "id": "electronics_store",
            "name": "Tienda de electrónica",
            "category": "Comercio"
        },
        {
            "id": "embassy",
            "name": "Embajada",
            "category": "Administración Pública"
        },
        {
            "id": "fire_station",
            "name": "Parque de bomberos",
            "category": "Servicios Públicos"
        },
        {
            "id": "florist",
            "name": "Floristería",
            "category": "Comercio"
        },
        {
            "id": "funeral_home",
            "name": "Funeraria",
            "category": "Servicios"
        },
        {
            "id": "furniture_store",
            "name": "Tienda de muebles",
            "category": "Comercio"
        },
        {
            "id": "gas_station",
            "name": "Gasolinera",
            "category": "Automoción"
        },
        {
            "id": "gym",
            "name": "Gimnasio",
            "category": "Deporte y Fitness"
        },
        {
            "id": "hair_care",
            "name": "Peluquería",
            "category": "Belleza y Spa"
        },
        {
            "id": "hardware_store",
            "name": "Ferretería",
            "category": "Comercio"
        },
        {
            "id": "hospital",
            "name": "Hospital",
            "category": "Salud"
        },
        {
            "id": "insurance_agency",
            "name": "Agencia de seguros",
            "category": "Servicios Financieros"
        },
        {
            "id": "jewelry_store",
            "name": "Joyería",
            "category": "Comercio"
        },
        {
            "id": "laundry",
            "name": "Lavandería",
            "category": "Servicios"
        },
        {
            "id": "lawyer",
            "name": "Abogado",
            "category": "Servicios Profesionales"
        },
        {
            "id": "library",
            "name": "Biblioteca",
            "category": "Educación"
        },
        {
            "id": "lodging",
            "name": "Alojamiento",
            "category": "Turismo"
        },
        {
            "id": "movie_theater",
            "name": "Cine",
            "category": "Entretenimiento"
        },
        {
            "id": "moving_company",
            "name": "Empresa de mudanzas",
            "category": "Servicios"
        },
        {
            "id": "museum",
            "name": "Museo",
            "category": "Arte y Cultura"
        },
        {
            "id": "night_club",
            "name": "Discoteca",
            "category": "Entretenimiento"
        },
        {
            "id": "painter",
            "name": "Pintor",
            "category": "Servicios"
        },
        {
            "id": "park",
            "name": "Parque",
            "category": "Ocio"
        },
        {
            "id": "parking",
            "name": "Aparcamiento",
            "category": "Transporte"
        },
        {
            "id": "pet_store",
            "name": "Tienda de mascotas",
            "category": "Comercio"
        },
        {
            "id": "pharmacy",
            "name": "Farmacia",
            "category": "Salud"
        },
        {
            "id": "physiotherapist",
            "name": "Fisioterapeuta",
            "category": "Salud"
        },
        {
            "id": "plumber",
            "name": "Fontanero",
            "category": "Servicios"
        },
        {
            "id": "police",
            "name": "Policía",
            "category": "Servicios Públicos"
        },
        {
            "id": "post_office",
            "name": "Oficina de correos",
            "category": "Servicios Públicos"
        },
        {
            "id": "real_estate_agency",
            "name": "Agencia inmobiliaria",
            "category": "Servicios Profesionales"
        },
        {
            "id": "restaurant",
            "name": "Restaurante",
            "category": "Gastronomía"
        },
        {
            "id": "roofing_contractor",
            "name": "Techador",
            "category": "Servicios"
        },
        {
            "id": "school",
            "name": "Escuela",
            "category": "Educación"
        },
        {
            "id": "shoe_store",
            "name": "Zapatería",
            "category": "Comercio"
        },
        {
            "id": "shopping_mall",
            "name": "Centro comercial",
            "category": "Comercio"
        },
        {
            "id": "spa",
            "name": "Spa",
            "category": "Belleza y Spa"
        },
        {
            "id": "stadium",
            "name": "Estadio",
            "category": "Deporte"
        },
        {
            "id": "storage",
            "name": "Almacenamiento",
            "category": "Servicios"
        },
        {
            "id": "store",
            "name": "Tienda",
            "category": "Comercio"
        },
        {
            "id": "supermarket",
            "name": "Supermercado",
            "category": "Comercio"
        },
        {
            "id": "taxi_stand",
            "name": "Parada de taxi",
            "category": "Transporte"
        },
        {
            "id": "tourist_attraction",
            "name": "Atracción turística",
            "category": "Turismo"
        },
        {
            "id": "train_station",
            "name": "Estación de tren",
            "category": "Transporte"
        },
        {
            "id": "travel_agency",
            "name": "Agencia de viajes",
            "category": "Turismo"
        },
        {
            "id": "university",
            "name": "Universidad",
            "category": "Educación"
        },
        {
            "id": "veterinary_care",
            "name": "Veterinario",
            "category": "Salud"
        },
        {
            "id": "zoo",
            "name": "Zoológico",
            "category": "Entretenimiento"
        }
    ]
    
    # Agrupar por categoría para facilitar la selección en el frontend
    categories = {}
    for place_type in place_types:
        category = place_type["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append(place_type)
    
    return jsonify({
        "types": place_types,
        "categories": categories
    })

@places_bp.route("/places/details/<place_id>", methods=["GET"])
@auth_optional
def get_details(place_id):
    """Obtener detalles de un lugar por su place_id"""
    if not place_id:
        return jsonify({"error": "Se requiere el parámetro 'place_id'"}), 400
    
    try:
        details = get_place_details(place_id)
        return jsonify(details)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@places_bp.route("/places/autocomplete", methods=["GET"])
@auth_optional
def autocomplete():
    """Obtener sugerencias de autocompletado para lugares"""
    input_text = request.args.get('input')
    location = request.args.get('location')
    radius = request.args.get('radius', type=int)
    types = request.args.get('types')
    
    if not input_text:
        return jsonify({"error": "Se requiere el parámetro 'input'"}), 400
    
    try:
        suggestions = get_place_autocomplete(input_text, location, radius, types)
        return jsonify({
            "suggestions": suggestions
        })
    except Exception as e:
        logger.error(f"Error en autocompletado: {str(e)}")
        return jsonify({"error": str(e)}), 500

@places_bp.route("/places/query-autocomplete", methods=["GET"])
@auth_optional
def query_autocomplete():
    """Obtener sugerencias de autocompletado para consultas de búsqueda"""
    input_text = request.args.get('input')
    location = request.args.get('location')
    radius = request.args.get('radius', type=int)
    
    if not input_text:
        return jsonify({"error": "Se requiere el parámetro 'input'"}), 400
    
    try:
        suggestions = get_query_autocomplete(input_text, location, radius)
        return jsonify({
            "suggestions": suggestions
        })
    except Exception as e:
        logger.error(f"Error en autocompletado de consulta: {str(e)}")
        return jsonify({"error": str(e)}), 500

@places_bp.route("/places/niche-suggestions", methods=["GET"])
@auth_optional
def niche_suggestions():
    """Obtener sugerencias de nichos de negocio"""
    input_text = request.args.get('input')
    
    if not input_text:
        return jsonify({"error": "Se requiere el parámetro 'input'"}), 400
    
    try:
        # Lista de nichos/categorías predefinidos que contienen el texto de entrada
        predefined_niches = [
            "Peluquería", "Barbería", "Clínica estética", "Clínicas estéticas", "Clínica dental", "Restaurante", 
            "Hotel", "Gimnasio", "Estudio de yoga", "Tienda de ropa", "Zapatería",
            "Panadería", "Pastelería", "Cafetería", "Floristería", "Librería",
            "Agencia inmobiliaria", "Agencia de viajes", "Agencia de marketing",
            "Academia de idiomas", "Autoescuela", "Centro de formación", "Guardería",
            "Clínica veterinaria", "Tienda de mascotas", "Centro de salud", "Hospital",
            "Farmacia", "Óptica", "Centro de fisioterapia", "Clínica de fisioterapia",
            "Estudio de tatuajes", "Clínica de nutrición", "Centro de nutrición",
            "Abogado", "Notaría", "Asesoría fiscal", "Gestoría", "Consultoría",
            "Bar", "Pub", "Discoteca", "Club", "Salón de eventos", "Salón de bodas",
            "Oficina de seguros", "Banco", "Cajero automático", "Casa de cambio",
            "Taller mecánico", "Lavadero de coches", "Gasolinera", "Estación de servicio",
            "Supermercado", "Hipermercado", "Mercado", "Frutería", "Carnicería", "Pescadería",
            "Ferretería", "Tienda de electrodomésticos", "Tienda de informática", "Tienda de móviles",
            "Estudio de fotografía", "Imprenta", "Copistería", "Papelería", "Juguetería",
            "Escuela de música", "Academia de baile", "Estudio de danza", "Centro cultural",
            "Museo", "Galería de arte", "Teatro", "Cine", "Parque de atracciones", "Parque acuático",
            "Spa", "Centro de belleza", "Centro de masajes", "Centro de depilación",
            "Salón de belleza", "Centro de estética", "Clínica de belleza", "Clínica estética",
            "Centro médico", "Centro de salud", "Consulta médica", "Consultorio médico",
            "Dentista", "Clínica dental", "Ortodoncista", "Implantes dentales",
            "Fontanero", "Electricista", "Carpintero", "Pintor", "Albañil", "Cerrajero",
            "Empresa de mudanzas", "Agencia de transportes", "Mensajería", "Correos",
            "Estudio de arquitectura", "Estudio de interiorismo", "Decoración", "Diseño de interiores",
            "Gimnasio", "Centro deportivo", "Club deportivo", "Piscina", "Campo de fútbol",
            "Cancha de tenis", "Pista de pádel", "Estudio de pilates", "Centro de yoga",
            "Estudio de pilates", "Entrenador personal", "Personal trainer"
        ]
        
        # Función para normalizar texto (quitar acentos/diacríticos)
        def normalize_text(text):
            return ''.join(c for c in unicodedata.normalize('NFD', text)
                          if unicodedata.category(c) != 'Mn').lower()
        
        # Normalizar texto de búsqueda
        search_term_normalized = normalize_text(input_text)
        
        # Filtrar por texto de entrada, usando texto normalizado para comparación
        filtered_niches = []
        for niche in predefined_niches:
            niche_normalized = normalize_text(niche)
            # Buscar coincidencias parciales en el texto normalizado
            if search_term_normalized in niche_normalized:
                filtered_niches.append(niche)
        
        # Poner los que comienzan con el texto de búsqueda primero (usando texto normalizado)
        starts_with = []
        contains = []
        
        for niche in filtered_niches:
            niche_normalized = normalize_text(niche)
            if niche_normalized.startswith(search_term_normalized):
                starts_with.append(niche)
            else:
                contains.append(niche)
        
        # Crear sugerencias con el formato adecuado para el frontend
        suggestions = []
        
        # Primero los que comienzan con el texto
        for niche in starts_with:
            suggestions.append({
                "description": niche,
                "isNiche": True,
                "terms": [niche]
            })
        
        # Luego los que contienen el texto
        for niche in contains:
            suggestions.append({
                "description": niche,
                "isNiche": True,
                "terms": [niche]
            })
        
        # Imprimir sugerencias para debug
        logger.info(f"Búsqueda: '{input_text}', Sugerencias encontradas: {len(suggestions)}")
        if suggestions:
            logger.info(f"Primeras sugerencias: {[s['description'] for s in suggestions[:5]]}")
        
        # Si hay pocas sugerencias, intentar obtener más dinámicamente
        if len(suggestions) < 5:
            # Usar query_autocomplete pero filtrar resultados para mostrar solo categorías
            dynamic_suggestions = get_query_autocomplete(input_text)
            # Filtrar para incluir solo entradas que parezcan categorías (sin direcciones específicas)
            filtered_dynamic = []
            
            for sugg in dynamic_suggestions:
                # Criterios para identificar categorías vs lugares específicos:
                # 1. No tiene comas (las direcciones suelen tener comas)
                # 2. No tiene números (las direcciones suelen tener números)
                # 3. No tiene más de 3 palabras (las categorías suelen ser breves)
                description = sugg["description"]
                
                # Contar palabras
                word_count = len(description.split())
                
                # Detectar si parece una dirección o un negocio específico
                has_comma = "," in description
                has_numbers = any(char.isdigit() for char in description)
                
                # Si parece una categoría
                if not has_comma and word_count <= 4 and (not has_numbers or word_count <= 2):
                    # Evitar duplicados con nuestras categorías predefinidas
                    if not any(normalize_text(s["description"]) == normalize_text(description) for s in suggestions):
                        filtered_dynamic.append({
                            "description": description,
                            "isNiche": True,
                            "terms": sugg.get("terms", [])
                        })
            
            # Añadir hasta 10 sugerencias dinámicas
            suggestions.extend(filtered_dynamic[:10])
        
        return jsonify({
            "suggestions": suggestions[:15]  # Limitamos a 15 sugerencias
        })
    except Exception as e:
        logger.error(f"Error en sugerencias de nichos: {str(e)}")
        return jsonify({"error": str(e)}), 500

@places_bp.route("/places/import", methods=["POST"])
@auth_optional
def import_to_db():
    """Importar places a la base de datos como leads, evitando duplicados por place_id"""
    db = current_app.config['MONGO_DB']
    places = request.json
    
    logger.info(f"Recibido para importar: {len(places) if places else 0} lugares")
    
    if not places or not isinstance(places, list):
        logger.error(f"Datos inválidos recibidos: {places}")
        return jsonify({"error": "Se requiere una lista de places"}), 400
    
    try:
        leads = []
        omitidos = 0
        
        for i, place in enumerate(places):
            logger.info(f"Procesando place {i+1}/{len(places)}: {place.get('name', 'Sin nombre')}")
            
            place_id = place.get("place_id", "")
            if not place_id:
                logger.warning(f"Place sin place_id: {place}")
                continue
                
            # Comprobar si ya existe
            if db.leads.find_one({"place_id": place_id}):
                logger.info(f"Place ya existe: {place_id}")
                omitidos += 1
                continue
                
            # Verificar los datos recibidos y su estructura
            logger.info(f"Datos del place: place_id={place_id}, name={place.get('name')}, " +
                       f"phone={place.get('formatted_phone_number')}, website={place.get('website')}, " +
                       f"address={place.get('formatted_address')}")
            
            lead = {
                "name": place.get("name", ""),
                "phone": place.get("formatted_phone_number", ""),
                "email": "",  # A completar con scraping
                "website": place.get("website", ""),
                "address": place.get("formatted_address", ""),
                "rating": place.get("rating", 0),
                "place_id": place_id,
                "source": "Google Places API"
            }
            leads.append(lead)
            
        logger.info(f"Total leads a importar: {len(leads)}")
        
        if leads:
            # Si hay algún error en la estructura de los datos, esto fallará
            logger.info(f"Intentando insertar {len(leads)} leads en la base de datos")
            try:
                result = db.leads.insert_many(leads)
                insertados = len(result.inserted_ids)
                logger.info(f"Insertados exitosamente: {insertados}")
            except Exception as e:
                logger.error(f"Error al insertar leads: {str(e)}")
                return jsonify({"error": f"Error al insertar en la base de datos: {str(e)}"}), 500
        else:
            insertados = 0
            logger.info("No hay leads nuevos para insertar")
            
        return jsonify({
            "message": f"Se importaron {insertados} leads correctamente. {omitidos} duplicados omitidos.",
            "insertados": insertados,
            "omitidos": omitidos
        }), 201
    except Exception as e:
        logger.exception(f"Error general en la importación: {str(e)}")
        return jsonify({"error": str(e)}), 500

@places_bp.route("/places/search/subdivide/stream", methods=["GET"])
@auth_optional
def search_subdivided_stream():
    """
    Buscar places utilizando la estrategia de subdivisión de área y transmitir 
    los resultados al cliente en tiempo real usando Server-Sent Events (SSE)
    """
    query = request.args.get('query')
    address = request.args.get('address')
    radius = request.args.get('radius', 5000, type=int)
    max_results = request.args.get('max_results', 500, type=int)
    max_depth = request.args.get('max_depth', 2, type=int)
    token = request.args.get('token')  # Obtener el token de la URL para SSE
    
    # Verificar token si está presente
    if token:
        try:
            from flask_jwt_extended import decode_token
            decode_token(token)
            # Si el token es válido, continuamos
        except Exception as e:
            logger.error(f"Token inválido en SSE: {str(e)}")
            if REQUIRE_AUTH:
                return jsonify({"error": "Token inválido o expirado"}), 401
    elif REQUIRE_AUTH:
        return jsonify({"error": "Se requiere autenticación"}), 401
    
    # Opción para no limitar resultados (0 = sin límite)
    if request.args.get('unlimited', 'false').lower() == 'true':
        max_results = 0
    
    if not query or not address:
        return jsonify({"error": "Se requieren los parámetros 'query' y 'address'"}), 400
    
    def generate_events():
        try:
            # Geocodificar la dirección
            geo = geocode_address(address)
            
            logger.info(f"Iniciando búsqueda subdividida streaming: {query} en {address} con radio {radius}m")
            
            # Enviar evento de inicio
            yield f"data: {json.dumps({'status': 'started', 'total_count': 0})}\n\n"
            
            # Función de callback para recibir resultados parciales
            def on_results(data):
                # Formatear los datos como SSE
                json_data = json.dumps(data)
                return f"data: {json_data}\n\n"
            
            # Este enfoque no funciona directamente con yield dentro de callback
            # Usamos una cola para recibir resultados
            from queue import Queue
            result_queue = Queue()
            
            # Callback real que pone resultados en la cola
            def queue_callback(data):
                result_queue.put(data)
            
            # Iniciar búsqueda en hilo separado para no bloquear
            def run_search():
                try:
                    subdivide_area_search(
                        query, geo['lat'], geo['lng'], radius, 
                        max_results, max_depth, 0, queue_callback
                    )
                    # Marcar finalización
                    result_queue.put(None)
                except Exception as e:
                    logger.error(f"Error en hilo de búsqueda: {str(e)}")
                    result_queue.put({"error": str(e), "status": "error"})
                    result_queue.put(None)
            
            # Iniciar hilo de búsqueda
            search_thread = Thread(target=run_search)
            search_thread.daemon = True
            search_thread.start()
            
            # Enviar ping periódicamente para mantener conexión viva
            last_event_time = time.time()
            ping_interval = 15  # segundos
            
            # Enviar resultados mientras llegan a la cola
            while True:
                try:
                    # Esperar un tiempo por nuevos resultados o enviar ping si es necesario
                    current_time = time.time()
                    timeout = max(0.1, min(1, ping_interval - (current_time - last_event_time)))
                    
                    try:
                        data = result_queue.get(timeout=timeout)
                        last_event_time = time.time()
                        
                        # None marca el final de la búsqueda
                        if data is None:
                            yield f"data: {json.dumps({'status': 'completed'})}\n\n"
                            break
                            
                        # Enviar datos
                        yield f"data: {json.dumps(data)}\n\n"
                        
                    except Exception:  # timeout de la cola
                        # Verificar si necesitamos enviar ping
                        if time.time() - last_event_time > ping_interval:
                            yield f"data: {json.dumps({'status': 'ping'})}\n\n"
                            last_event_time = time.time()
                            
                except Exception as e:
                    logger.error(f"Error al generar eventos SSE: {str(e)}")
                    yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
                    break
            
        except Exception as e:
            logger.error(f"Error global en streaming: {str(e)}")
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
    
    # Configurar la respuesta como SSE
    return Response(
        stream_with_context(generate_events()),
        mimetype="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',  # Necesario para Nginx
            'Connection': 'keep-alive'
        }
    )

@places_bp.route("/places/search/by-type/subdivide/stream", methods=["GET"])
@auth_optional
def search_by_type_subdivided_stream():
    """
    Buscar places por tipo utilizando la estrategia de subdivisión de área y transmitir 
    los resultados al cliente en tiempo real usando Server-Sent Events (SSE)
    """
    place_type = request.args.get('type')
    address = request.args.get('address')
    radius = request.args.get('radius', 5000, type=int)
    max_results = request.args.get('max_results', 500, type=int)
    max_depth = request.args.get('max_depth', 2, type=int)
    token = request.args.get('token')  # Obtener el token de la URL para SSE
    
    # Verificar token si está presente
    if token:
        try:
            from flask_jwt_extended import decode_token
            decode_token(token)
            # Si el token es válido, continuamos
        except Exception as e:
            logger.error(f"Token inválido en SSE: {str(e)}")
            if REQUIRE_AUTH:
                return jsonify({"error": "Token inválido o expirado"}), 401
    elif REQUIRE_AUTH:
        return jsonify({"error": "Se requiere autenticación"}), 401
    
    # Opción para no limitar resultados (0 = sin límite)
    if request.args.get('unlimited', 'false').lower() == 'true':
        max_results = 0
    
    if not place_type or not address:
        return jsonify({"error": "Se requieren los parámetros 'type' y 'address'"}), 400
    
    def generate_events():
        try:
            # Geocodificar la dirección
            geo = geocode_address(address)
            
            logger.info(f"Iniciando búsqueda por tipo subdividida streaming: {place_type} en {address} con radio {radius}m")
            
            # Enviar evento de inicio
            yield f"data: {json.dumps({'status': 'started', 'total_count': 0})}\n\n"
            
            # Usar cola para recibir resultados
            from queue import Queue
            result_queue = Queue()
            
            # Callback que pone resultados en la cola
            def queue_callback(data):
                result_queue.put(data)
            
            # Iniciar búsqueda en hilo separado para no bloquear
            def run_search():
                try:
                    subdivide_area_search_by_type(
                        place_type, geo['lat'], geo['lng'], radius, 
                        max_results, max_depth, 0, queue_callback
                    )
                    # Marcar finalización
                    result_queue.put(None)
                except Exception as e:
                    logger.error(f"Error en hilo de búsqueda: {str(e)}")
                    result_queue.put({"error": str(e), "status": "error"})
                    result_queue.put(None)
            
            # Iniciar hilo de búsqueda
            search_thread = Thread(target=run_search)
            search_thread.daemon = True
            search_thread.start()
            
            # Enviar ping periódicamente para mantener conexión viva
            last_event_time = time.time()
            ping_interval = 15  # segundos
            
            # Enviar resultados mientras llegan a la cola
            while True:
                try:
                    # Esperar un tiempo por nuevos resultados o enviar ping si es necesario
                    current_time = time.time()
                    timeout = max(0.1, min(1, ping_interval - (current_time - last_event_time)))
                    
                    try:
                        data = result_queue.get(timeout=timeout)
                        last_event_time = time.time()
                        
                        # None marca el final de la búsqueda
                        if data is None:
                            yield f"data: {json.dumps({'status': 'completed'})}\n\n"
                            break
                            
                        # Enviar datos
                        yield f"data: {json.dumps(data)}\n\n"
                        
                    except Exception:  # timeout de la cola
                        # Verificar si necesitamos enviar ping
                        if time.time() - last_event_time > ping_interval:
                            yield f"data: {json.dumps({'status': 'ping'})}\n\n"
                            last_event_time = time.time()
                            
                except Exception as e:
                    logger.error(f"Error al generar eventos SSE: {str(e)}")
                    yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
                    break
            
        except Exception as e:
            logger.error(f"Error global en streaming: {str(e)}")
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
    
    # Configurar la respuesta como SSE
    return Response(
        stream_with_context(generate_events()),
        mimetype="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',  # Necesario para Nginx
            'Connection': 'keep-alive'
        }
    ) 