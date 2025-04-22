from flask import Blueprint, request, jsonify, current_app
from bson.objectid import ObjectId
import jwt
from app.models.integration import Integration
from app.models.user_mapping import UserMapping
from app.models.card_channel_mapping import CardChannelMapping
from app.services.trello_service import TrelloService
from app.services.discord_service import DiscordService
import os
import requests
from datetime import datetime
from trello import TrelloClient
from app.discord.bot import create_discord_channel, send_message_to_channel, send_message_with_button

integration_bp = Blueprint('integration', __name__)

# Servicios
trello_service = None
discord_service = None

def get_trello_service():
    """
    Obtiene una instancia del cliente de Trello
    """
    api_key = os.environ.get('TRELLO_API_KEY')
    token = os.environ.get('TRELLO_TOKEN')
    
    if not api_key or not token:
        raise ValueError("Credenciales de Trello no configuradas")
    
    return TrelloClient(
        api_key=api_key,
        token=token
    )

def get_discord_service():
    global discord_service
    if discord_service is None:
        discord_service = DiscordService()
    return discord_service

# Middleware para verificar el token JWT
def token_required(f):
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            token = auth_header.split(" ")[1] if len(auth_header.split(" ")) > 1 else None
        
        if not token:
            return jsonify({'message': 'Token no proporcionado'}), 401
        
        try:
            # Verificar token
            data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            # En auth.py se usa 'sub' en lugar de 'user_id'
            current_user_id = data['sub']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expirado. Inicia sesión nuevamente.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token inválido. Inicia sesión nuevamente.'}), 401
        except Exception as e:
            current_app.logger.error(f"Error al verificar token: {e}")
            return jsonify({'message': 'Error al validar la sesión'}), 401
        
        return f(current_user_id, *args, **kwargs)
    
    decorated.__name__ = f.__name__
    return decorated

# Rutas de integración
@integration_bp.route('/', methods=['POST'])
@token_required
def create_integration(current_user_id):
    """
    Crea una nueva integración
    """
    try:
        current_app.logger.info(f"Intento de creación de integración por usuario: {current_user_id}")
        db = current_app.config['MONGO_DB']
        data = request.get_json()
        
        if not data:
            current_app.logger.warning("Datos de integración no proporcionados")
            return jsonify({'message': 'No se proporcionaron datos para la integración'}), 400
            
        # Validar datos requeridos
        required_fields = ['trello_board_id', 'discord_server_id']
        missing_fields = [field for field in required_fields if field not in data or not data[field]]
        if missing_fields:
            current_app.logger.warning(f"Campos requeridos faltantes: {missing_fields}")
            return jsonify({'message': f'Los siguientes campos son requeridos: {", ".join(missing_fields)}'}), 400
        
        # Validar que los IDs tengan formato esperado
        if not data['trello_board_id'] or not isinstance(data['trello_board_id'], str) or data['trello_board_id'].strip() == '':
            current_app.logger.warning(f"ID de tablero de Trello inválido: {data.get('trello_board_id')}")
            return jsonify({'message': 'ID de tablero de Trello inválido'}), 400
            
        if not data['discord_server_id'] or not isinstance(data['discord_server_id'], str) or data['discord_server_id'].strip() == '':
            current_app.logger.warning(f"ID de servidor de Discord inválido: {data.get('discord_server_id')}")
            return jsonify({'message': 'ID de servidor de Discord inválido'}), 400
            
        # Verificar si la integración ya existe para este usuario y tablero
        existing_integration = db.integrations.find_one({
            'created_by': ObjectId(current_user_id),
            'trello_board_id': data['trello_board_id'],
            'discord_server_id': data['discord_server_id']
        })
        
        if existing_integration:
            current_app.logger.warning(f"Ya existe una integración para este tablero y servidor: {existing_integration['_id']}")
            return jsonify({'message': 'Ya existe una integración para este tablero y servidor de Discord'}), 409
        
        # Datos de la integración
        integration_data = {
            'trello_board_id': data['trello_board_id'],
            'discord_server_id': data['discord_server_id'],
            'webhook_id': data.get('webhook_id', ''),  # Puede ser opcional o generado posteriormente
            'created_by': ObjectId(current_user_id),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'active': True,
            'name': data.get('name', 'Integración sin nombre'),
            'trello_board_name': data.get('trello_board_name', ''),
            'trello_board_url': data.get('trello_board_url', '')
        }
        
        # Insertar en la base de datos
        result = db.integrations.insert_one(integration_data)
        
        # Verificar si se insertó correctamente
        if not result.inserted_id:
            current_app.logger.error("No se pudo crear la integración: el ID insertado es nulo")
            return jsonify({'message': 'Error al crear la integración: no se generó un ID válido'}), 500
            
        # Confirmar que el ID es válido
        if not ObjectId.is_valid(result.inserted_id):
            current_app.logger.error(f"ID generado no válido: {result.inserted_id}")
            return jsonify({'message': 'Error al crear la integración: ID generado no válido'}), 500
            
        current_app.logger.info(f"Integración creada con ID: {result.inserted_id}")
        
        # Devolver la integración creada
        integration_data['_id'] = str(result.inserted_id)
        integration_data['created_by'] = str(integration_data['created_by'])
        return jsonify(integration_data), 201
    except Exception as e:
        current_app.logger.error(f"Error al crear integración: {e}")
        return jsonify({'message': f'Error al crear integración: {str(e)}'}), 500

@integration_bp.route('/', methods=['GET'])
@token_required
def get_integrations(current_user_id):
    """
    Obtiene todas las integraciones del usuario
    """
    try:
        db = current_app.config['MONGO_DB']
        
        # Obtener integraciones del usuario
        integrations = list(db.integrations.find({'created_by': ObjectId(current_user_id)}))
        
        # Lista para almacenar integraciones válidas
        valid_integrations = []
        
        # Convertir ObjectId a string y validar integraciones
        for integration in integrations:
            # Verificar que tenga _id válido
            if '_id' not in integration or not integration['_id']:
                current_app.logger.warning(f"Integración sin _id encontrada: {integration}")
                continue
                
            # Convertir ObjectId a string
            integration['_id'] = str(integration['_id'])
            
            # Verificar que el _id convertido sea válido
            if integration['_id'] == 'None' or integration['_id'] == 'undefined' or integration['_id'].strip() == '':
                current_app.logger.warning(f"Integración con _id inválido: {integration}")
                continue
                
            if 'created_by' in integration:
                integration['created_by'] = str(integration['created_by'])
                
            # Solo añadir integraciones con _id válido
            valid_integrations.append(integration)
        
        current_app.logger.info(f"Integraciones obtenidas: {len(valid_integrations)} de {len(integrations)} totales")
        return jsonify(valid_integrations), 200
    except Exception as e:
        current_app.logger.error(f"Error al obtener integraciones: {e}")
        return jsonify({'message': f'Error al obtener integraciones: {str(e)}'}), 500

@integration_bp.route('/<integration_id>', methods=['GET'])
@token_required
def get_integration(current_user_id, integration_id):
    """
    Obtiene una integración por su ID
    """
    try:
        db = current_app.config['MONGO_DB']
        
        # Obtener integración
        integration = db.integrations.find_one({
            '_id': ObjectId(integration_id),
            'created_by': ObjectId(current_user_id)
        })
        
        if not integration:
            return jsonify({'message': 'Integración no encontrada'}), 404
        
        # Convertir ObjectId a string
        integration['_id'] = str(integration['_id'])
        integration['created_by'] = str(integration['created_by'])
        
        return jsonify({'integration': integration}), 200
    except Exception as e:
        current_app.logger.error(f"Error al obtener integración: {e}")
        return jsonify({'message': f'Error al obtener integración: {str(e)}'}), 500

@integration_bp.route('/<integration_id>', methods=['DELETE'])
@token_required
def delete_integration(current_user_id, integration_id):
    """
    Elimina una integración específica
    """
    try:
        current_app.logger.info(f"Intento de eliminación de integración con ID: {integration_id} por usuario: {current_user_id}")
        
        # Validar que el ID sea válido antes de intentar convertirlo
        if not integration_id:
            current_app.logger.warning(f"Intento de eliminar integración con ID nulo o vacío")
            return jsonify({'message': 'ID de integración no proporcionado'}), 400
            
        if integration_id == 'None' or integration_id == 'undefined' or integration_id.strip() == '':
            current_app.logger.warning(f"Intento de eliminar integración con ID inválido: {integration_id}")
            return jsonify({'message': f'ID de integración inválido: {integration_id}'}), 400
        
        try:
            # Intentar convertir a ObjectId para verificar si tiene el formato correcto
            object_id = ObjectId(integration_id)
        except Exception as e:
            current_app.logger.warning(f"Error al convertir ID de integración a ObjectId: {integration_id}, Error: {e}")
            return jsonify({'message': f'ID de integración con formato inválido: {integration_id}'}), 400
            
        db = current_app.config['MONGO_DB']
        
        # Primero verificar si la integración existe
        integration = db.integrations.find_one({'_id': ObjectId(integration_id)})
        if not integration:
            current_app.logger.warning(f"Integración no encontrada con ID: {integration_id}")
            return jsonify({'message': 'Integración no encontrada'}), 404
            
        # Verificar si el usuario actual es el creador de la integración
        if 'created_by' in integration and str(integration['created_by']) != str(current_user_id):
            current_app.logger.warning(f"Usuario {current_user_id} intentó eliminar integración {integration_id} que pertenece a {integration.get('created_by')}")
            return jsonify({'message': 'No tienes permiso para eliminar esta integración'}), 403
            
        # Eliminar la integración
        result = db.integrations.delete_one({'_id': ObjectId(integration_id)})
        
        if result.deleted_count == 0:
            current_app.logger.error(f"Error al eliminar integración con ID: {integration_id}, no se eliminó ningún documento")
            return jsonify({'message': 'No se pudo eliminar la integración'}), 500
            
        current_app.logger.info(f"Integración eliminada con éxito, ID: {integration_id}")
        
        # También eliminar registros relacionados
        try:
            card_states_result = db.card_states.delete_many({'integration_id': ObjectId(integration_id)})
            current_app.logger.info(f"Se eliminaron {card_states_result.deleted_count} registros de estados de tarjetas para la integración {integration_id}")
            
            mappings_result = db.user_mappings.delete_many({'integration_id': ObjectId(integration_id)})
            current_app.logger.info(f"Se eliminaron {mappings_result.deleted_count} mapeos de usuarios para la integración {integration_id}")
            
            card_mappings_result = db.card_channel_mappings.delete_many({'integration_id': ObjectId(integration_id)})
            current_app.logger.info(f"Se eliminaron {card_mappings_result.deleted_count} mapeos de tarjetas para la integración {integration_id}")
        except Exception as e:
            # No fallamos la operación principal si falla la eliminación de registros relacionados
            current_app.logger.error(f"Error al eliminar registros relacionados para la integración {integration_id}: {e}")
        
        return jsonify({'message': 'Integración eliminada correctamente'}), 200
    except Exception as e:
        current_app.logger.error(f"Error inesperado al eliminar integración: {e}")
        return jsonify({'message': f'Error al eliminar integración: {str(e)}'}), 500

@integration_bp.route('/test/trello-connection', methods=['GET'])
def test_trello_connection():
    """
    Endpoint para verificar la conexión con Trello
    No requiere autenticación para facilitar la depuración
    """
    try:
        api_key = os.environ.get('TRELLO_API_KEY')
        token = os.environ.get('TRELLO_TOKEN')
        
        if not api_key or not token:
            return jsonify({
                'status': 'error',
                'message': 'Credenciales de Trello no configuradas',
                'api_key_present': bool(api_key),
                'token_present': bool(token)
            }), 400
        
        # Intentar hacer una solicitud directa a la API para obtener información del usuario
        url = "https://api.trello.com/1/members/me"
        headers = {
            "Accept": "application/json"
        }
        query = {
            'key': api_key,
            'token': token
        }
        
        response = requests.get(url, headers=headers, params=query)
        
        # Verificar la respuesta
        if response.status_code == 200:
            user_data = response.json()
            return jsonify({
                'status': 'success',
                'message': 'Conexión con Trello exitosa',
                'user_info': {
                    'id': user_data.get('id'),
                    'username': user_data.get('username'),
                    'fullName': user_data.get('fullName')
                },
                'api_key': api_key[:5] + '...',
                'token': token[:5] + '...',
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': f'Error al conectar con Trello: HTTP {response.status_code}',
                'response_text': response.text,
                'api_key': api_key[:5] + '...',
                'token': token[:5] + '...',
            }), 400
    except Exception as e:
        current_app.logger.error(f"Error al verificar conexión con Trello: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error al conectar con Trello: {str(e)}'
        }), 500

@integration_bp.route('/<integration_id>/check-updates', methods=['POST'])
@token_required
def check_integration_updates(current_user_id, integration_id):
    """
    Comprueba manualmente si hay actualizaciones en un tablero de Trello
    Este endpoint simula lo que haría un webhook
    """
    try:
        db = current_app.config['MONGO_DB']
        
        # Obtener integración
        integration = db.integrations.find_one({
            '_id': ObjectId(integration_id),
            'created_by': ObjectId(current_user_id)
        })
        
        if not integration:
            return jsonify({'message': 'Integración no encontrada'}), 404
        
        # Obtener las tarjetas actuales del tablero
        try:
            cards_response = requests.get(
                f"{os.environ.get('WEBHOOK_BASE_URL')}/api/debug/trello/board/{integration['trello_board_id']}/cards",
                headers={"Accept": "application/json"}
            )
            
            if cards_response.status_code != 200:
                return jsonify({
                    'message': 'Error al obtener tarjetas actuales',
                    'details': cards_response.text
                }), 500
                
            current_cards = cards_response.json().get('cards', [])
            
            # Obtener el estado anterior de las tarjetas
            previous_cards = list(db.card_states.find({
                'integration_id': ObjectId(integration_id)
            }))
            
            # Convertir a diccionario para búsqueda más rápida
            previous_cards_dict = {card['card_id']: card for card in previous_cards}
            
            # Variables para seguimiento de cambios
            new_cards = []
            modified_cards = []
            moved_cards = []
            
            # Comprobar cambios
            for card in current_cards:
                if card['id'] not in previous_cards_dict:
                    # Nueva tarjeta
                    new_cards.append(card)
                    
                    # Guardar estado de la nueva tarjeta
                    card_state = {
                        'integration_id': ObjectId(integration_id),
                        'card_id': card['id'],
                        'name': card['name'],
                        'id_list': card['id_list'],
                        'last_modified': datetime.utcnow(),
                        'is_processed': False  # Marcar como no procesada
                    }
                    db.card_states.insert_one(card_state)
                else:
                    # Tarjeta existente - comprobar cambios
                    prev_state = previous_cards_dict[card['id']]
                    
                    if prev_state['name'] != card['name']:
                        # Nombre modificado
                        modified_cards.append({
                            'card': card,
                            'previous': prev_state,
                            'change_type': 'name'
                        })
                        
                        # Actualizar estado
                        db.card_states.update_one(
                            {'_id': prev_state['_id']},
                            {'$set': {
                                'name': card['name'],
                                'last_modified': datetime.utcnow(),
                                'is_processed': False
                            }}
                        )
                    
                    if prev_state['id_list'] != card['id_list']:
                        # Tarjeta movida a otra lista
                        moved_cards.append({
                            'card': card,
                            'previous': prev_state,
                            'change_type': 'list',
                            'from_list': prev_state['id_list'],
                            'to_list': card['id_list']
                        })
                        
                        # Actualizar estado
                        db.card_states.update_one(
                            {'_id': prev_state['_id']},
                            {'$set': {
                                'id_list': card['id_list'],
                                'last_modified': datetime.utcnow(),
                                'is_processed': False
                            }}
                        )
            
            # Actualizar la fecha de última comprobación
            db.integrations.update_one(
                {'_id': ObjectId(integration_id)},
                {'$set': {'last_check': datetime.utcnow()}}
            )
            
            # Retornar información sobre los cambios detectados
            return jsonify({
                'message': 'Comprobación de cambios completada',
                'changes': {
                    'new_cards': len(new_cards),
                    'modified_cards': len(modified_cards),
                    'moved_cards': len(moved_cards)
                },
                'details': {
                    'new_cards': [{
                        'id': card['id'],
                        'name': card['name'],
                        'list': card['id_list']
                    } for card in new_cards],
                    'modified_cards': [{
                        'id': change['card']['id'],
                        'old_name': change['previous']['name'],
                        'new_name': change['card']['name']
                    } for change in modified_cards],
                    'moved_cards': [{
                        'id': change['card']['id'],
                        'name': change['card']['name'],
                        'from_list': change['from_list'],
                        'to_list': change['to_list']
                    } for change in moved_cards]
                }
            }), 200
        except Exception as e:
            current_app.logger.error(f"Error al comprobar cambios: {e}")
            return jsonify({'message': f'Error al comprobar cambios: {str(e)}'}), 500
    except Exception as e:
        current_app.logger.error(f"Error al acceder a la integración: {e}")
        return jsonify({'message': f'Error al acceder a la integración: {str(e)}'}), 500

@integration_bp.route('/<integration_id>/pending-changes', methods=['GET'])
@token_required
def get_pending_changes(current_user_id, integration_id):
    """
    Obtiene los cambios pendientes de procesamiento para una integración
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
        
        # Buscar tarjetas no procesadas
        pending_cards = list(db.card_states.find({
            'integration_id': ObjectId(integration_id),
            'is_processed': False
        }))
        
        # Convertir ObjectId a string
        for card in pending_cards:
            card['_id'] = str(card['_id'])
            card['integration_id'] = str(card['integration_id'])
            
            # Convertir datetime a ISO string para JSON
            if card.get('last_modified'):
                card['last_modified'] = card['last_modified'].isoformat()
        
        # Obtener información sobre las listas
        try:
            lists_response = requests.get(
                f"{os.environ.get('WEBHOOK_BASE_URL')}/api/debug/trello/board/{integration['trello_board_id']}/details",
                headers={"Accept": "application/json"}
            )
            
            if lists_response.status_code == 200:
                lists_data = lists_response.json().get('lists', [])
                lists_dict = {lst['id']: lst['name'] for lst in lists_data}
                
                # Añadir nombres de listas a las tarjetas
                for card in pending_cards:
                    card['list_name'] = lists_dict.get(card['id_list'], 'Lista desconocida')
        except Exception as e:
            current_app.logger.warning(f"Error al obtener nombres de listas: {e}")
            # No fallamos la operación completa por esto
        
        return jsonify({
            'integration': {
                'id': str(integration['_id']),
                'trello_board_id': integration['trello_board_id'],
                'trello_board_name': integration.get('trello_board_name', 'Tablero sin nombre'),
                'discord_server_id': integration['discord_server_id'],
                'last_check': integration.get('last_check', '').isoformat() if integration.get('last_check') else None
            },
            'pending_changes': len(pending_cards),
            'cards': pending_cards
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error al obtener cambios pendientes: {e}")
        return jsonify({'message': f'Error al obtener cambios pendientes: {str(e)}'}), 500

@integration_bp.route('/<integration_id>/mark-processed', methods=['POST'])
@token_required
def mark_changes_processed(current_user_id, integration_id):
    """
    Marca como procesados los cambios pendientes de una integración
    """
    try:
        card_ids = request.json.get('card_ids', [])
        if not card_ids:
            return jsonify({'message': 'No se proporcionaron IDs de tarjetas'}), 400
        
        db = current_app.config['MONGO_DB']
        
        # Verificar que la integración exista y pertenezca al usuario
        integration = db.integrations.find_one({
            '_id': ObjectId(integration_id),
            'created_by': ObjectId(current_user_id)
        })
        
        if not integration:
            return jsonify({'message': 'Integración no encontrada'}), 404
        
        # Marcar las tarjetas como procesadas
        result = db.card_states.update_many(
            {
                'integration_id': ObjectId(integration_id),
                'card_id': {'$in': card_ids}
            },
            {'$set': {'is_processed': True}}
        )
        
        return jsonify({
            'message': 'Cambios marcados como procesados',
            'processed_count': result.modified_count
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error al marcar cambios como procesados: {e}")
        return jsonify({'message': f'Error al marcar cambios como procesados: {str(e)}'}), 500

@integration_bp.route('/trello-discord/test-channel', methods=['POST'])
def test_discord_channel():
    """
    Prueba la creación de un canal en Discord
    """
    try:
        data = request.get_json()
        
        if not data or 'channel_name' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Se requiere un nombre de canal'
            }), 400
        
        channel_name = data['channel_name']
        
        # Crear el canal en Discord
        channel_id = create_discord_channel(channel_name)
        
        if not channel_id:
            return jsonify({
                'status': 'error',
                'message': 'No se pudo crear el canal en Discord'
            }), 500
        
        # Enviar un mensaje de prueba si se creó el canal correctamente
        message = data.get('message', 'Este es un mensaje de prueba desde la integración Trello-Discord')
        
        message_sent = send_message_to_channel(channel_id, message)
        
        return jsonify({
            'status': 'success',
            'message': 'Canal creado correctamente',
            'channel_id': channel_id,
            'message_sent': message_sent
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error al probar la integración con Discord: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error al probar la integración: {str(e)}'
        }), 500

@integration_bp.route('/trello-discord/send-message', methods=['POST'])
def send_discord_message():
    """
    Envía un mensaje a un canal existente de Discord
    """
    try:
        data = request.get_json()
        
        if not data or 'channel_id' not in data or 'message' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Se requiere un ID de canal y un mensaje'
            }), 400
        
        channel_id = data['channel_id']
        message = data['message']
        
        # Enviar el mensaje al canal
        message_sent = send_message_to_channel(channel_id, message)
        
        if not message_sent:
            return jsonify({
                'status': 'error',
                'message': 'No se pudo enviar el mensaje a Discord'
            }), 500
        
        return jsonify({
            'status': 'success',
            'message': 'Mensaje enviado correctamente',
            'channel_id': channel_id
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error al enviar mensaje a Discord: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error al enviar mensaje: {str(e)}'
        }), 500

@integration_bp.route('/mapping/user', methods=['POST'])
def map_users():
    """
    Crea o actualiza un mapeo entre un usuario de Trello y un usuario de Discord
    """
    try:
        data = request.get_json()
        
        if not data or 'trello_user_id' not in data or 'discord_user_id' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Se requiere un ID de usuario de Trello y un ID de usuario de Discord'
            }), 400
        
        trello_user_id = data['trello_user_id']
        discord_user_id = data['discord_user_id']
        
        # TODO: Implementar la lógica para guardar el mapeo en la base de datos
        # Esto dependerá de cómo estés estructurando tu base de datos
        
        # Por ahora, simplemente devolvemos éxito
        return jsonify({
            'status': 'success',
            'message': 'Mapeo de usuario guardado',
            'trello_user_id': trello_user_id,
            'discord_user_id': discord_user_id
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error al mapear usuarios: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error al mapear usuarios: {str(e)}'
        }), 500

@integration_bp.route('/mapping/card-channel', methods=['POST'])
def map_card_channel():
    """
    Crea o actualiza un mapeo entre una tarjeta de Trello y un canal de Discord
    """
    try:
        data = request.get_json()
        
        if not data or 'trello_card_id' not in data or 'discord_channel_id' not in data:
            return jsonify({
                'status': 'error',
                'message': 'Se requiere un ID de tarjeta de Trello y un ID de canal de Discord'
            }), 400
        
        trello_card_id = data['trello_card_id']
        discord_channel_id = data['discord_channel_id']
        
        # TODO: Implementar la lógica para guardar el mapeo en la base de datos
        # Esto dependerá de cómo estés estructurando tu base de datos
        
        # Por ahora, simplemente devolvemos éxito
        return jsonify({
            'status': 'success',
            'message': 'Mapeo de tarjeta-canal guardado',
            'trello_card_id': trello_card_id,
            'discord_channel_id': discord_channel_id
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error al mapear tarjeta-canal: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error al mapear tarjeta-canal: {str(e)}'
        }), 500

# Función para actualizar una tarjeta de Trello cuando un usuario confirma
def update_trello_card_with_confirmation(card_id, user_id, action="confirm"):
    """
    Actualiza una tarjeta en Trello cuando un usuario confirma mediante Discord.
    """
    try:
        current_app.logger.info(f"[Trello] Iniciando actualización de tarjeta: card_id={card_id}, user_id={user_id}, action={action}")
        # Obtener credenciales de Trello
        api_key = os.environ.get('TRELLO_API_KEY')
        token = os.environ.get('TRELLO_TOKEN')
        
        if not api_key or not token:
            current_app.logger.error("[Trello] Credenciales de Trello no configuradas")
            return False
        
        # Buscar el ID de usuario de Trello correspondiente al ID de Discord
        db = current_app.config['MONGO_DB']
        user_mapping = db.user_mappings.find_one({'discord_user_id': user_id})
        current_app.logger.info(f"[Trello] user_mapping encontrado: {user_mapping}")
        
        if not user_mapping or 'trello_user_id' not in user_mapping:
            current_app.logger.error(f"[Trello] No se encontró mapeo para el usuario de Discord: {user_id}")
            return False
        
        trello_user_id = user_mapping['trello_user_id']
        
        # Dependiendo del tipo de acción, realizamos diferentes operaciones
        if action == "confirm":
            # Añadir un comentario a la tarjeta indicando la confirmación
            comment_url = f"https://api.trello.com/1/cards/{card_id}/actions/comments"
            comment_params = {
                'key': api_key,
                'token': token,
                'text': f"✅ Tarea confirmada por el usuario a través de Discord."
            }
            current_app.logger.info(f"[Trello] Enviando comentario a {comment_url} con params {comment_params}")
            
            comment_response = requests.post(comment_url, params=comment_params)
            current_app.logger.info(f"[Trello] Respuesta de comentario: status={comment_response.status_code}, body={comment_response.text}")
            
            if comment_response.status_code != 200:
                current_app.logger.error(f"[Trello] Error al añadir comentario a la tarjeta: HTTP {comment_response.status_code}")
                return False
            
            # Opcionalmente, añadir una etiqueta verde a la tarjeta
            card_details_url = f"https://api.trello.com/1/cards/{card_id}"
            card_details_params = {
                'key': api_key,
                'token': token,
                'fields': 'idBoard'
            }
            current_app.logger.info(f"[Trello] Obteniendo detalles de la tarjeta: {card_details_url} params={card_details_params}")
            card_response = requests.get(card_details_url, params=card_details_params)
            current_app.logger.info(f"[Trello] Respuesta detalles tarjeta: status={card_response.status_code}, body={card_response.text}")
            
            if card_response.status_code == 200:
                board_id = card_response.json().get('idBoard')
                
                # Obtener o crear una etiqueta verde de "Confirmado"
                labels_url = f"https://api.trello.com/1/boards/{board_id}/labels"
                labels_params = {
                    'key': api_key,
                    'token': token
                }
                current_app.logger.info(f"[Trello] Obteniendo etiquetas del tablero: {labels_url} params={labels_params}")
                labels_response = requests.get(labels_url, params=labels_params)
                current_app.logger.info(f"[Trello] Respuesta etiquetas: status={labels_response.status_code}, body={labels_response.text}")
                
                if labels_response.status_code == 200:
                    labels = labels_response.json()
                    confirmed_label_id = None
                    
                    # Buscar una etiqueta verde con nombre "Confirmado"
                    for label in labels:
                        if label.get('color') == 'green' and label.get('name') == 'Confirmado':
                            confirmed_label_id = label.get('id')
                            break
                    
                    # Si no existe, crear la etiqueta
                    if not confirmed_label_id:
                        create_label_url = f"https://api.trello.com/1/labels"
                        create_label_params = {
                            'key': api_key,
                            'token': token,
                            'name': 'Confirmado',
                            'color': 'green',
                            'idBoard': board_id
                        }
                        current_app.logger.info(f"[Trello] Creando etiqueta: {create_label_url} params={create_label_params}")
                        create_label_response = requests.post(create_label_url, params=create_label_params)
                        current_app.logger.info(f"[Trello] Respuesta crear etiqueta: status={create_label_response.status_code}, body={create_label_response.text}")
                        
                        if create_label_response.status_code == 200:
                            confirmed_label_id = create_label_response.json().get('id')
                        else:
                            current_app.logger.error(f"[Trello] No se pudo crear la etiqueta: HTTP {create_label_response.status_code}")
                    
                    # Añadir la etiqueta a la tarjeta
                    if confirmed_label_id:
                        add_label_url = f"https://api.trello.com/1/cards/{card_id}/idLabels"
                        add_label_params = {
                            'key': api_key,
                            'token': token,
                            'value': confirmed_label_id
                        }
                        current_app.logger.info(f"[Trello] Añadiendo etiqueta a la tarjeta: {add_label_url} params={add_label_params}")
                        add_label_response = requests.post(add_label_url, params=add_label_params)
                        current_app.logger.info(f"[Trello] Respuesta añadir etiqueta: status={add_label_response.status_code}, body={add_label_response.text}")
                        
                        if add_label_response.status_code != 200:
                            current_app.logger.error(f"[Trello] Error al añadir etiqueta a la tarjeta: HTTP {add_label_response.status_code}")
            
            current_app.logger.info(f"[Trello] Tarjeta {card_id} confirmada por usuario Discord {user_id} (Trello: {trello_user_id})")
            return True
        
        # Otros tipos de acciones podrían implementarse aquí
        
        return False
    
    except Exception as e:
        current_app.logger.error(f"[Trello] Error al actualizar tarjeta de Trello con confirmación: {e}")
        import traceback
        current_app.logger.error(traceback.format_exc())
        return False

@integration_bp.route('/trello/webhook', methods=['POST'])
def trello_webhook():
    """
    Endpoint para recibir webhooks de Trello
    """
    data = request.json
    
    if not data:
        return jsonify({
            'status': 'error',
            'message': 'No data received'
        }), 400
    
    # Procesar los datos del webhook (implementación pendiente)
    
    return jsonify({
        'status': 'success',
        'message': 'Webhook received'
    }), 200

@integration_bp.route('/trello/test-connection', methods=['GET'])
def test_trello_connection_endpoint():
    """
    Endpoint para probar la conexión con Trello
    """
    try:
        service = get_trello_service()
        
        # Verificar el formato de retorno de get_trello_service
        api_key_preview = ''
        if isinstance(service, dict) and 'api_key' in service:
            api_key_preview = service['api_key'][:5] + '...'
        elif hasattr(service, 'api_key'):
            api_key_preview = service.api_key[:5] + '...'
        
        return jsonify({
            'status': 'success',
            'message': 'Trello connection successful',
            'api_key': api_key_preview
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@integration_bp.route('/discord/test-message', methods=['POST'])
def test_discord_message():
    """
    Endpoint para probar el envío de mensajes a Discord
    """
    data = request.json
    
    if not data or 'channel_id' not in data or 'message' not in data:
        return jsonify({
            'status': 'error',
            'message': 'Missing channel_id or message'
        }), 400
    
    channel_id = data['channel_id']
    message = data['message']
    
    result = send_message_to_channel(channel_id, message)
    
    if result:
        return jsonify({
            'status': 'success',
            'message': 'Message sent to Discord'
        }), 200
    else:
        return jsonify({
            'status': 'error',
            'message': 'Failed to send message to Discord'
        }), 500

@integration_bp.route('/discord/test-message-with-button', methods=['POST'])
def test_discord_message_with_button_endpoint():
    """
    Endpoint para probar el envío de mensajes con botones a Discord
    """
    data = request.json
    
    if not data or 'channel_id' not in data or 'message' not in data:
        return jsonify({
            'status': 'error',
            'message': 'Missing channel_id or message'
        }), 400
    
    channel_id = data['channel_id']
    message = data['message']
    button_label = data.get('button_label', 'Confirmar')
    trello_card_id = data.get('trello_card_id', 'test_card_id')
    user_id = data.get('user_id', 'test_user_id')
    action = data.get('action', 'confirm')
    
    result = send_message_with_button(channel_id, message, button_label, trello_card_id, user_id, action)
    
    if result:
        return jsonify({
            'status': 'success',
            'message': 'Message with button sent to Discord'
        }), 200
    else:
        return jsonify({
            'status': 'error',
            'message': 'Failed to send message with button to Discord'
        }), 500 