from flask import Blueprint, request, jsonify, current_app
from app.services.places_service import search_places, get_place_details
from app.services.geocoding_service import geocode_address
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import logging

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
        results, next_token = search_places(query, latlng, radius, max_results, next_page_token, fetch_all)
        return jsonify({
            "results": results,
            "next_page_token": next_token
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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