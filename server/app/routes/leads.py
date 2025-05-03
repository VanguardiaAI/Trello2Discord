from flask import Blueprint, request, jsonify, current_app, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
import csv
from io import StringIO
import os

leads_bp = Blueprint('leads', __name__)

# Definir si queremos autenticación obligatoria o no (para desarrollo)
REQUIRE_AUTH = os.environ.get('REQUIRE_AUTH', 'false').lower() == 'true'

# Decorador personalizado para hacer jwt_required opcional según la configuración
def auth_optional(fn):
    if REQUIRE_AUTH:
        return jwt_required()(fn)
    return fn

@leads_bp.route("/leads", methods=["GET"])
@auth_optional
def get_leads():
    """Obtener todos los leads"""
    db = current_app.config['MONGO_DB']
    leads = list(db.leads.find({}, {"_id": 0}))
    return jsonify(leads)

@leads_bp.route("/leads/<lead_id>", methods=["GET"])
@auth_optional
def get_lead(lead_id):
    """Obtener un lead por su ID"""
    db = current_app.config['MONGO_DB']
    lead = db.leads.find_one({"place_id": lead_id}, {"_id": 0})
    if not lead:
        return jsonify({"error": "Lead no encontrado"}), 404
    return jsonify(lead)

@leads_bp.route("/leads", methods=["POST"])
@auth_optional
def create_lead():
    """Crear un nuevo lead"""
    db = current_app.config['MONGO_DB']
    data = request.json
    if not data:
        return jsonify({"error": "Datos no proporcionados"}), 400
    
    required_fields = ["name"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Campo '{field}' requerido"}), 400
    
    # Comprobar si el lead ya existe por place_id
    if data.get("place_id") and db.leads.find_one({"place_id": data["place_id"]}):
        return jsonify({"error": "Ya existe un lead con ese place_id"}), 400
    
    result = db.leads.insert_one(data)
    return jsonify({"message": "Lead creado correctamente", "id": str(result.inserted_id)}), 201

@leads_bp.route("/leads/<lead_id>", methods=["PUT"])
@auth_optional
def update_lead(lead_id):
    """Actualizar un lead existente"""
    db = current_app.config['MONGO_DB']
    data = request.json
    if not data:
        return jsonify({"error": "Datos no proporcionados"}), 400
    
    result = db.leads.update_one({"place_id": lead_id}, {"$set": data})
    if result.matched_count == 0:
        return jsonify({"error": "Lead no encontrado"}), 404
    
    return jsonify({"message": "Lead actualizado correctamente"}), 200

@leads_bp.route("/leads/<lead_id>", methods=["DELETE"])
@auth_optional
def delete_lead(lead_id):
    """Eliminar un lead"""
    db = current_app.config['MONGO_DB']
    result = db.leads.delete_one({"place_id": lead_id})
    if result.deleted_count == 0:
        return jsonify({"error": "Lead no encontrado"}), 404
    
    return jsonify({"message": "Lead eliminado correctamente"}), 200

@leads_bp.route("/leads/export", methods=["GET"])
@auth_optional
def export_leads():
    """Exportar leads a CSV"""
    db = current_app.config['MONGO_DB']
    leads = list(db.leads.find({}, {"_id": 0}))
    
    if not leads:
        return jsonify({"error": "No hay leads para exportar"}), 404
    
    csv_output = StringIO()
    csv_writer = csv.DictWriter(csv_output, fieldnames=leads[0].keys())
    csv_writer.writeheader()
    csv_writer.writerows(leads)
    
    return Response(
        csv_output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=leads.csv"}
    ) 