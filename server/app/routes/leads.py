from flask import Blueprint, request, jsonify, current_app, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
import csv
from io import StringIO
import os
from datetime import datetime

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
    
    # Añadir campos para gestión de leads
    if "status" not in data:
        data["status"] = "Nuevo"
    if "labels" not in data:
        data["labels"] = []
    if "notes" not in data:
        data["notes"] = []
    if "created_at" not in data:
        data["created_at"] = datetime.now().isoformat()
    if "updated_at" not in data:
        data["updated_at"] = datetime.now().isoformat()
    
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
    
    # Actualizar timestamp
    data["updated_at"] = datetime.now().isoformat()
    
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

@leads_bp.route("/leads/batch/delete", methods=["POST"])
@auth_optional
def batch_delete_leads():
    """Eliminar múltiples leads"""
    db = current_app.config['MONGO_DB']
    data = request.json
    
    if not data or "leads" not in data or not isinstance(data["leads"], list):
        return jsonify({"error": "Se requiere una lista de IDs de leads"}), 400
    
    lead_ids = data["leads"]
    if not lead_ids:
        return jsonify({"error": "Lista de IDs vacía"}), 400
    
    result = db.leads.delete_many({"place_id": {"$in": lead_ids}})
    
    return jsonify({
        "message": f"Se eliminaron {result.deleted_count} leads correctamente",
        "deleted_count": result.deleted_count
    }), 200

@leads_bp.route("/leads/batch/update", methods=["POST"])
@auth_optional
def batch_update_leads():
    """Actualizar múltiples leads con etiquetas o estados"""
    db = current_app.config['MONGO_DB']
    data = request.json
    
    if not data or "leads" not in data or not isinstance(data["leads"], list):
        return jsonify({"error": "Se requiere una lista de IDs de leads"}), 400
    
    lead_ids = data["leads"]
    if not lead_ids:
        return jsonify({"error": "Lista de IDs vacía"}), 400
    
    update_data = {}
    
    # Actualizar estado
    if "status" in data:
        update_data["status"] = data["status"]
    
    # Actualizar etiquetas
    if "add_labels" in data and isinstance(data["add_labels"], list):
        # Utilizamos un operador de actualización para arrays
        result = db.leads.update_many(
            {"place_id": {"$in": lead_ids}},
            {"$addToSet": {"labels": {"$each": data["add_labels"]}}}
        )
    
    # Eliminar etiquetas
    if "remove_labels" in data and isinstance(data["remove_labels"], list):
        result = db.leads.update_many(
            {"place_id": {"$in": lead_ids}},
            {"$pull": {"labels": {"$in": data["remove_labels"]}}}
        )
    
    # Actualizar campos simples
    if update_data:
        update_data["updated_at"] = datetime.now().isoformat()
        result = db.leads.update_many(
            {"place_id": {"$in": lead_ids}},
            {"$set": update_data}
        )
    
    return jsonify({
        "message": f"Se actualizaron {result.modified_count} leads correctamente",
        "modified_count": result.modified_count
    }), 200

@leads_bp.route("/leads/<lead_id>/notes", methods=["POST"])
@auth_optional
def add_note_to_lead(lead_id):
    """Añadir una nota a un lead"""
    db = current_app.config['MONGO_DB']
    data = request.json
    
    if not data or "content" not in data:
        return jsonify({"error": "Se requiere el contenido de la nota"}), 400
    
    note = {
        "content": data["content"],
        "created_at": datetime.now().isoformat(),
        "id": datetime.now().timestamp()
    }
    
    result = db.leads.update_one(
        {"place_id": lead_id},
        {
            "$push": {"notes": note},
            "$set": {"updated_at": datetime.now().isoformat()}
        }
    )
    
    if result.matched_count == 0:
        return jsonify({"error": "Lead no encontrado"}), 404
    
    return jsonify({
        "message": "Nota añadida correctamente",
        "note": note
    }), 201

@leads_bp.route("/leads/<lead_id>/notes/<note_id>", methods=["DELETE"])
@auth_optional
def delete_note_from_lead(lead_id, note_id):
    """Eliminar una nota de un lead"""
    db = current_app.config['MONGO_DB']
    
    try:
        note_id_float = float(note_id)
    except ValueError:
        return jsonify({"error": "ID de nota inválido"}), 400
    
    result = db.leads.update_one(
        {"place_id": lead_id},
        {
            "$pull": {"notes": {"id": note_id_float}},
            "$set": {"updated_at": datetime.now().isoformat()}
        }
    )
    
    if result.matched_count == 0:
        return jsonify({"error": "Lead no encontrado"}), 404
    
    return jsonify({
        "message": "Nota eliminada correctamente"
    }), 200

@leads_bp.route("/leads/labels", methods=["GET"])
@auth_optional
def get_all_labels():
    """Obtener todas las etiquetas únicas usadas en la base de datos"""
    db = current_app.config['MONGO_DB']
    
    # Primero, obtener etiquetas personalizadas guardadas
    custom_labels = list(db.custom_labels.find({}, {"_id": 0, "label": 1}))
    saved_labels = [item["label"] for item in custom_labels]
    
    # Segundo, obtener etiquetas de los leads
    pipeline = [
        {"$unwind": "$labels"},
        {"$group": {"_id": "$labels"}},
        {"$project": {"label": "$_id", "_id": 0}}
    ]
    
    results = list(db.leads.aggregate(pipeline))
    lead_labels = [result["label"] for result in results]
    
    # Combinar y eliminar duplicados
    all_labels = list(set(saved_labels + lead_labels))
    
    return jsonify(all_labels)

@leads_bp.route("/leads/labels", methods=["POST"])
@auth_optional
def save_custom_label():
    """Guardar una etiqueta personalizada en la base de datos"""
    db = current_app.config['MONGO_DB']
    data = request.json
    
    if not data or "label" not in data:
        return jsonify({"error": "Se requiere el nombre de la etiqueta"}), 400
    
    label = data["label"].strip()
    if not label:
        return jsonify({"error": "La etiqueta no puede estar vacía"}), 400
    
    # Comprobar si la etiqueta ya existe
    if db.custom_labels.find_one({"label": label}):
        return jsonify({"message": "La etiqueta ya existe", "label": label}), 200
    
    # Guardar la etiqueta
    db.custom_labels.insert_one({
        "label": label,
        "created_at": datetime.now().isoformat()
    })
    
    return jsonify({"message": "Etiqueta guardada correctamente", "label": label}), 201

@leads_bp.route("/leads/labels/<label>", methods=["DELETE"])
@auth_optional
def delete_custom_label(label):
    """Eliminar una etiqueta personalizada"""
    db = current_app.config['MONGO_DB']
    
    result = db.custom_labels.delete_one({"label": label})
    
    if result.deleted_count == 0:
        return jsonify({"error": "Etiqueta no encontrada"}), 404
    
    return jsonify({"message": "Etiqueta eliminada correctamente"}), 200

@leads_bp.route("/leads/export", methods=["GET"])
@auth_optional
def export_leads():
    """Exportar leads a CSV"""
    db = current_app.config['MONGO_DB']
    leads = list(db.leads.find({}, {"_id": 0}))
    
    if not leads:
        return jsonify({"error": "No hay leads para exportar"}), 404
    
    # Procesar las etiquetas y notas para el CSV
    for lead in leads:
        if "labels" in lead and isinstance(lead["labels"], list):
            lead["labels"] = ", ".join(lead["labels"])
        if "notes" in lead and isinstance(lead["notes"], list):
            notes_texts = [note.get("content", "") for note in lead["notes"]]
            lead["notes"] = " | ".join(notes_texts)
    
    # Recopilar todos los campos posibles para asegurar consistencia
    all_fields = set()
    for lead in leads:
        all_fields.update(lead.keys())
    
    all_fields = sorted(list(all_fields))  # Ordenar para consistencia
    
    # Asegurarse de que todos los leads tienen todos los campos
    for lead in leads:
        for field in all_fields:
            if field not in lead:
                lead[field] = ""  # Valor por defecto para campos faltantes
    
    csv_output = StringIO()
    csv_writer = csv.DictWriter(csv_output, fieldnames=all_fields)
    csv_writer.writeheader()
    csv_writer.writerows(leads)
    
    # Crear respuesta con los encabezados CORS necesarios
    response = Response(
        csv_output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment;filename=leads.csv",
            "Access-Control-Allow-Origin": "*",  # O especificar el origen exacto: "http://localhost:5173"
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        }
    )
    
    return response 