from flask import Blueprint, request, jsonify, current_app
from bson.objectid import ObjectId
import jwt
from app.models.user_mapping import UserMapping
from app.routes.integration import token_required, get_trello_service, get_discord_service

user_mapping_bp = Blueprint('user_mapping', __name__)

@user_mapping_bp.route('/integration/<integration_id>/users/trello', methods=['GET'])
@token_required
def get_trello_users(current_user_id, integration_id):
    """
    Obtiene los usuarios de Trello para una integración
    """
    try:
        db = current_app.config['MONGO_DB']
        
        # Verificar que la integración exista y pertenezca al usuario
        integration = db.integrations.find_one({
            '_id': ObjectId(integration_id),
            'created_by': ObjectId(current_user_id)
        })
        
        if not integration:
            return jsonify({'message': 'Integración no encontrada'}), 404
        
        # Obtener usuarios de Trello
        trello_users = get_trello_service().get_board_members(integration['trello_board_id'])
        
        # Formatear usuarios
        formatted_users = []
        for user in trello_users:
            formatted_users.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name
            })
        
        return jsonify({'trello_users': formatted_users}), 200
    except Exception as e:
        current_app.logger.error(f"Error al obtener usuarios de Trello: {e}")
        return jsonify({'message': f'Error al obtener usuarios de Trello: {str(e)}'}), 500

@user_mapping_bp.route('/integration/<integration_id>/users/discord', methods=['GET'])
@token_required
def get_discord_users(current_user_id, integration_id):
    """
    Obtiene los usuarios de Discord para una integración
    """
    try:
        db = current_app.config['MONGO_DB']
        
        # Verificar que la integración exista y pertenezca al usuario
        integration = db.integrations.find_one({
            '_id': ObjectId(integration_id),
            'created_by': ObjectId(current_user_id)
        })
        
        if not integration:
            return jsonify({'message': 'Integración no encontrada'}), 404
        
        # Obtener usuarios de Discord
        discord_users = get_discord_service().get_guild_members_sync(integration['discord_server_id'])
        
        return jsonify({'discord_users': discord_users}), 200
    except Exception as e:
        current_app.logger.error(f"Error al obtener usuarios de Discord: {e}")
        return jsonify({'message': f'Error al obtener usuarios de Discord: {str(e)}'}), 500

@user_mapping_bp.route('/integration/<integration_id>/mapping', methods=['POST'])
@token_required
def create_user_mapping(current_user_id, integration_id):
    """
    Crea un mapeo entre un usuario de Trello y un usuario de Discord
    """
    try:
        data = request.json
        
        # Validar datos
        if not data or 'trello_user_id' not in data or 'discord_user_id' not in data:
            return jsonify({'message': 'Datos incompletos'}), 400
        
        db = current_app.config['MONGO_DB']
        
        # Verificar que la integración exista y pertenezca al usuario
        integration = db.integrations.find_one({
            '_id': ObjectId(integration_id),
            'created_by': ObjectId(current_user_id)
        })
        
        if not integration:
            return jsonify({'message': 'Integración no encontrada'}), 404
        
        # Verificar si ya existe un mapeo para este usuario de Trello en esta integración
        existing_mapping = db.user_mappings.find_one({
            'trello_user_id': data['trello_user_id'],
            'integration_id': ObjectId(integration_id)
        })
        
        if existing_mapping:
            return jsonify({'message': 'Ya existe un mapeo para este usuario de Trello'}), 400
        
        # Obtener información de los usuarios
        trello_users = get_trello_service().get_board_members(integration['trello_board_id'])
        discord_users = get_discord_service().get_guild_members_sync(integration['discord_server_id'])
        
        trello_user = next((u for u in trello_users if u.id == data['trello_user_id']), None)
        discord_user = next((u for u in discord_users if u['id'] == data['discord_user_id']), None)
        
        if not trello_user:
            return jsonify({'message': 'Usuario de Trello no encontrado en el tablero'}), 404
        
        if not discord_user:
            return jsonify({'message': 'Usuario de Discord no encontrado en el servidor'}), 404
        
        # Crear mapeo
        user_mapping = UserMapping(
            trello_user_id=data['trello_user_id'],
            trello_username=trello_user.username,
            discord_user_id=data['discord_user_id'],
            discord_username=discord_user['username'],
            integration_id=ObjectId(integration_id),
            created_by=ObjectId(current_user_id)
        )
        
        # Guardar en base de datos
        mapping_id = db.user_mappings.insert_one(user_mapping.to_dict()).inserted_id
        
        return jsonify({
            'message': 'Mapeo de usuario creado exitosamente',
            'mapping_id': str(mapping_id)
        }), 201
    except Exception as e:
        current_app.logger.error(f"Error al crear mapeo de usuario: {e}")
        return jsonify({'message': f'Error al crear mapeo de usuario: {str(e)}'}), 500

@user_mapping_bp.route('/integration/<integration_id>/mapping', methods=['GET'])
@token_required
def get_user_mappings(current_user_id, integration_id):
    """
    Obtiene todos los mapeos de usuarios para una integración
    """
    try:
        db = current_app.config['MONGO_DB']
        
        # Verificar que la integración exista y pertenezca al usuario
        integration = db.integrations.find_one({
            '_id': ObjectId(integration_id),
            'created_by': ObjectId(current_user_id)
        })
        
        if not integration:
            return jsonify({'message': 'Integración no encontrada'}), 404
        
        # Obtener mapeos
        mappings = list(db.user_mappings.find({'integration_id': ObjectId(integration_id)}))
        
        # Convertir ObjectId a string
        for mapping in mappings:
            mapping['_id'] = str(mapping['_id'])
            mapping['integration_id'] = str(mapping['integration_id'])
            mapping['created_by'] = str(mapping['created_by'])
        
        return jsonify({'mappings': mappings}), 200
    except Exception as e:
        current_app.logger.error(f"Error al obtener mapeos de usuarios: {e}")
        return jsonify({'message': f'Error al obtener mapeos de usuarios: {str(e)}'}), 500

@user_mapping_bp.route('/mapping/<mapping_id>', methods=['DELETE'])
@token_required
def delete_user_mapping(current_user_id, mapping_id):
    """
    Elimina un mapeo de usuario por su ID
    """
    try:
        db = current_app.config['MONGO_DB']
        
        # Obtener mapeo
        mapping = db.user_mappings.find_one({'_id': ObjectId(mapping_id)})
        
        if not mapping:
            return jsonify({'message': 'Mapeo no encontrado'}), 404
        
        # Verificar que la integración pertenezca al usuario
        integration = db.integrations.find_one({
            '_id': mapping['integration_id'],
            'created_by': ObjectId(current_user_id)
        })
        
        if not integration:
            return jsonify({'message': 'No autorizado para eliminar este mapeo'}), 403
        
        # Eliminar mapeo
        db.user_mappings.delete_one({'_id': ObjectId(mapping_id)})
        
        return jsonify({'message': 'Mapeo eliminado exitosamente'}), 200
    except Exception as e:
        current_app.logger.error(f"Error al eliminar mapeo de usuario: {e}")
        return jsonify({'message': f'Error al eliminar mapeo de usuario: {str(e)}'}), 500

@user_mapping_bp.route('/create-direct', methods=['POST'])
@token_required
def create_direct_mapping(current_user_id):
    """
    Crea un mapeo directo entre un usuario de Trello y un usuario de Discord
    sin tener que consultar las APIs externas (solución para problemas con la API de Trello)
    """
    try:
        current_app.logger.info("Intento de crear mapeo directo")
        data = request.json
        
        # Validar datos requeridos
        required_fields = ['trello_user_id', 'trello_username', 'discord_user_id', 
                          'discord_username', 'integration_id']
        
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        if missing_fields:
            current_app.logger.warning(f"Campos faltantes para crear mapeo directo: {missing_fields}")
            return jsonify({'message': f'Campos requeridos faltantes: {", ".join(missing_fields)}'}), 400
        
        db = current_app.config['MONGO_DB']
        
        # Verificar que la integración exista y pertenezca al usuario
        try:
            integration_id = ObjectId(data['integration_id'])
            integration = db.integrations.find_one({
                '_id': integration_id,
                'created_by': ObjectId(current_user_id)
            })
            
            if not integration:
                current_app.logger.warning(f"Integración no encontrada o no pertenece al usuario: {data['integration_id']}")
                return jsonify({'message': 'Integración no encontrada o no tienes permisos'}), 404
        except Exception as e:
            current_app.logger.error(f"Error al verificar integración: {e}")
            return jsonify({'message': 'ID de integración inválido'}), 400
            
        # Verificar si ya existe un mapeo para este usuario de Trello en esta integración
        existing_mapping = db.user_mappings.find_one({
            'trello_user_id': data['trello_user_id'],
            'integration_id': integration_id
        })
        
        if existing_mapping:
            current_app.logger.warning(f"Ya existe un mapeo para el usuario de Trello: {data['trello_user_id']}")
            return jsonify({'message': 'Ya existe un mapeo para este usuario de Trello'}), 400
        
        # Crear mapeo
        user_mapping = UserMapping(
            trello_user_id=data['trello_user_id'],
            trello_username=data['trello_username'],
            discord_user_id=data['discord_user_id'],
            discord_username=data['discord_username'],
            integration_id=integration_id,
            created_by=ObjectId(current_user_id)
        )
        
        # Guardar en base de datos
        mapping_id = db.user_mappings.insert_one(user_mapping.to_dict()).inserted_id
        
        current_app.logger.info(f"Mapeo directo creado con éxito, ID: {mapping_id}")
        
        return jsonify({
            'message': 'Mapeo de usuario creado exitosamente',
            'mapping_id': str(mapping_id)
        }), 201
    except Exception as e:
        current_app.logger.error(f"Error al crear mapeo directo: {e}")
        return jsonify({'message': f'Error al crear mapeo directo: {str(e)}'}), 500 