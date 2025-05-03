from flask import Blueprint, request, jsonify, current_app
from bson.objectid import ObjectId
from app.models.card_channel_mapping import CardChannelMapping
from app.routes.integration import token_required, get_trello_service, get_discord_service

card_channel_bp = Blueprint('card_channel', __name__)

@card_channel_bp.route('/integration/<integration_id>/lists', methods=['GET'])
@token_required
def get_trello_lists(current_user_id, integration_id):
    """
    Obtiene las listas de Trello para una integración
    """
    try:
        import os
        import requests
        db = current_app.config['MONGO_DB']
        integration = db.integrations.find_one({
            '_id': ObjectId(integration_id),
            'created_by': ObjectId(current_user_id)
        })
        if not integration:
            return jsonify({'message': 'Integración no encontrada'}), 404
        trello_board_id = integration['trello_board_id']
        api_key = os.environ.get('TRELLO_API_KEY')
        token = os.environ.get('TRELLO_TOKEN')
        url = f"https://api.trello.com/1/boards/{trello_board_id}/lists"
        params = {
            'key': api_key,
            'token': token,
            'fields': 'id,name,closed'
        }
        response = requests.get(url, params=params)
        if response.status_code != 200:
            current_app.logger.error(f"Error al obtener listas de Trello: {response.text}")
            return jsonify({'message': f'Error al obtener listas de Trello: {response.text}'}), 500
        lists_data = response.json()
        formatted_lists = []
        for lst in lists_data:
            formatted_lists.append({
                'id': lst.get('id'),
                'name': lst.get('name')
            })
        return jsonify({'trello_lists': formatted_lists}), 200
    except Exception as e:
        current_app.logger.error(f"Error al obtener listas de Trello: {e}")
        return jsonify({'message': f'Error al obtener listas de Trello: {str(e)}'}), 500

@card_channel_bp.route('/integration/<integration_id>/channels', methods=['GET'])
@token_required
def get_discord_channels(current_user_id, integration_id):
    """
    Obtiene los canales de texto de Discord para una integración
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
        
        # Obtener canales de Discord
        discord_channels = get_discord_service().get_channels_sync(integration['discord_server_id'])
        
        return jsonify({'discord_channels': discord_channels}), 200
    except Exception as e:
        current_app.logger.error(f"Error al obtener canales de Discord: {e}")
        return jsonify({'message': f'Error al obtener canales de Discord: {str(e)}'}), 500

@card_channel_bp.route('/integration/<integration_id>/mapping', methods=['POST'])
@token_required
def create_list_channel_mapping(current_user_id, integration_id):
    """
    Crea un mapeo manual entre una lista de Trello y un canal de Discord
    """
    try:
        import os
        import requests
        data = request.json
        if not data or 'trello_list_id' not in data or 'discord_channel_id' not in data:
            return jsonify({'message': 'Datos incompletos'}), 400
        db = current_app.config['MONGO_DB']
        integration = db.integrations.find_one({
            '_id': ObjectId(integration_id),
            'created_by': ObjectId(current_user_id)
        })
        if not integration:
            return jsonify({'message': 'Integración no encontrada'}), 404
        existing_mapping = db.card_channel_mappings.find_one({
            'trello_list_id': data['trello_list_id'],
            'integration_id': ObjectId(integration_id)
        })
        if existing_mapping:
            return jsonify({'message': 'Ya existe un mapeo para esta lista'}), 400
        existing_channel_mapping = db.card_channel_mappings.find_one({
            'discord_channel_id': data['discord_channel_id'],
            'integration_id': ObjectId(integration_id)
        })
        if existing_channel_mapping:
            return jsonify({'message': 'Ya existe un mapeo para este canal'}), 400
        # Obtener información de la lista desde la API de Trello
        trello_board_id = integration['trello_board_id']
        api_key = os.environ.get('TRELLO_API_KEY')
        token = os.environ.get('TRELLO_TOKEN')
        url = f"https://api.trello.com/1/boards/{trello_board_id}/lists"
        params = {
            'key': api_key,
            'token': token,
            'fields': 'id,name,closed'
        }
        response = requests.get(url, params=params)
        if response.status_code != 200:
            current_app.logger.error(f"Error al obtener listas de Trello: {response.text}")
            return jsonify({'message': f'Error al obtener listas de Trello: {response.text}'}), 500
        lists_data = response.json()
        current_app.logger.info(f"ID de lista recibido: {data['trello_list_id']}")
        current_app.logger.info(f"IDs de listas obtenidas: {[l.get('id') for l in lists_data]}")
        list_obj = next((l for l in lists_data if l.get('id') == data['trello_list_id']), None)
        if not list_obj:
            current_app.logger.error(f"No se encontró la lista con ID {data['trello_list_id']} en las listas del tablero {trello_board_id}")
            return jsonify({'message': 'Lista de Trello no encontrada'}), 404
        discord_channels = get_discord_service().get_channels_sync(integration['discord_server_id'])
        channel = next((c for c in discord_channels if c['id'] == data['discord_channel_id']), None)
        if not channel:
            return jsonify({'message': 'Canal de Discord no encontrado en el servidor'}), 404
        list_channel_mapping = CardChannelMapping(
            trello_list_id=data['trello_list_id'],
            trello_list_name=list_obj.get('name'),
            discord_channel_id=data['discord_channel_id'],
            discord_channel_name=channel['name'],
            integration_id=ObjectId(integration_id),
            created_by=ObjectId(current_user_id),
            created_automatically=False
        )
        mapping_id = db.card_channel_mappings.insert_one(list_channel_mapping.to_dict()).inserted_id
        if not mapping_id or not ObjectId.is_valid(mapping_id):
            current_app.logger.error(f"Error al crear mapeo: ID generado inválido: {mapping_id}")
            return jsonify({'message': 'Error al crear el mapeo: ID generado inválido'}), 500
        current_app.logger.info(f"Mapeo creado exitosamente: {mapping_id}")
        message_content = f"**Lista de Trello vinculada manualmente: {list_obj.get('name')}**\n\n"
        message = get_discord_service().send_message_sync(
            data['discord_channel_id'],
            message_content
        )
        if message:
            db.card_channel_mappings.update_one(
                {'_id': ObjectId(mapping_id)},
                {'$set': {'discord_message_id': message['id']}}
            )
        
        # Obtener y procesar todas las tarjetas existentes en esta lista
        try:
            current_app.logger.info(f"Procesando tarjetas existentes para la lista {data['trello_list_id']}")
            # Obtener tarjetas de esta lista
            cards_url = f"https://api.trello.com/1/lists/{data['trello_list_id']}/cards"
            cards_params = {
                'key': api_key,
                'token': token,
                'fields': 'id,name,desc,idList,idMembers,dateLastActivity,shortUrl,due,labels',
                'attachments': 'true',
                'attachment_fields': 'id,name,url,bytes,date',
            }
            cards_response = requests.get(cards_url, params=cards_params)
            if cards_response.status_code == 200:
                cards = cards_response.json()
                current_app.logger.info(f"Se encontraron {len(cards)} tarjetas en la lista {data['trello_list_id']}")
                
                # Importar funciones necesarias de debug.py
                from app.discord.bot import send_message_to_channel, send_message_with_button
                from app.routes.debug import get_discord_user_id, get_trello_member_details
                
                # Procesar cada tarjeta como si fuera nueva
                for card in cards:
                    try:
                        # Si la tarjeta tiene asignados, enviar mensaje con botón de confirmación
                        assigned_discord_users = [get_discord_user_id(mid) for mid in card.get('idMembers', []) if get_discord_user_id(mid)]
                        if assigned_discord_users:
                            for member_id in card.get('idMembers', []):
                                discord_user_id = get_discord_user_id(member_id)
                                if discord_user_id:
                                    confirmation_message = (
                                        f"📄 **Tarea:** {card['name']}\n"
                                    )
                                    if card.get('desc'):
                                        confirmation_message += f"📝 **Descripción:** {card.get('desc')}\n"
                                    if card.get('due'):
                                        confirmation_message += f"📅 **Fecha límite:** {card.get('due')}\n"
                                    if card.get('labels'):
                                        etiquetas = ', '.join([label.get('name', '') for label in card.get('labels', []) if label.get('name')])
                                        if etiquetas:
                                            confirmation_message += f"🏷️ **Etiquetas:** {etiquetas}\n"
                                    if card.get('attachments'):
                                        adjuntos = card['attachments']
                                        if adjuntos:
                                            confirmation_message += "📎 **Adjuntos:**\n"
                                            for adj in adjuntos:
                                                confirmation_message += f"- {adj.get('name', 'Archivo')}\n"
                                    confirmation_message += f"🙋‍♂️ **Asignado a:** <@{discord_user_id}>\n"
                                    if card.get('shortUrl'):
                                        confirmation_message += f"\n📌 **Enlace a la tarjeta:** {card.get('shortUrl')}\n"
                                    confirmation_message += "\nPor favor, confirma que vista esta asignación haciendo clic en el botón:"
                                    send_message_with_button(
                                        data['discord_channel_id'],
                                        confirmation_message,
                                        "Confirmar asignación",
                                        card['id'],
                                        discord_user_id,
                                        "confirm"
                                    )
                        else:
                            # Si no hay asignados, solo enviar mensaje informativo
                            message = f"**Tarjeta existente en Trello**\n"
                            message += f"📄 **Tarea:** {card['name']}\n"
                            if card.get('desc'):
                                message += f"📝 **Descripción:** {card.get('desc')}\n"
                            if card.get('due'):
                                message += f"📅 **Fecha límite:** {card.get('due')}\n"
                            if card.get('labels'):
                                etiquetas = ', '.join([label.get('name', '') for label in card.get('labels', []) if label.get('name')])
                                if etiquetas:
                                    message += f"🏷️ **Etiquetas:** {etiquetas}\n"
                            if card.get('attachments'):
                                adjuntos = card['attachments']
                                if adjuntos:
                                    message += "📎 **Adjuntos:**\n"
                                    for adj in adjuntos:
                                        message += f"- {adj.get('name', 'Archivo')}\n"
                            if card.get('shortUrl'):
                                message += f"\n📌 **Enlace a la tarjeta:** {card.get('shortUrl')}\n"
                            send_message_to_channel(data['discord_channel_id'], message)
                    except Exception as e:
                        current_app.logger.error(f"Error al procesar tarjeta {card.get('id')}: {e}")
                        continue
            else:
                current_app.logger.error(f"Error al obtener tarjetas de la lista: HTTP {cards_response.status_code}")
        except Exception as e:
            current_app.logger.error(f"Error al procesar tarjetas existentes: {e}")
            # No retornamos error, continuamos con el proceso principal
        
        return jsonify({
            'message': 'Mapeo de lista-canal creado exitosamente',
            'mapping_id': str(mapping_id)
        }), 201
    except Exception as e:
        current_app.logger.error(f"Error al crear mapeo de lista-canal: {e}")
        return jsonify({'message': f'Error al crear mapeo de lista-canal: {str(e)}'}), 500

@card_channel_bp.route('/integration/<integration_id>/mapping', methods=['GET'])
@token_required
def get_list_channel_mappings(current_user_id, integration_id):
    """
    Obtiene todos los mapeos de listas-canales para una integración
    """
    try:
        db = current_app.config['MONGO_DB']
        integration = db.integrations.find_one({
            '_id': ObjectId(integration_id),
            'created_by': ObjectId(current_user_id)
        })
        if not integration:
            return jsonify({'message': 'Integración no encontrada'}), 404
        mappings = list(db.card_channel_mappings.find({'integration_id': ObjectId(integration_id)}))
        for mapping in mappings:
            mapping['_id'] = str(mapping['_id'])
            mapping['integration_id'] = str(mapping['integration_id'])
            if 'created_by' in mapping and mapping['created_by']:
                mapping['created_by'] = str(mapping['created_by'])
        return jsonify({'mappings': mappings}), 200
    except Exception as e:
        current_app.logger.error(f"Error al obtener mapeos de listas-canales: {e}")
        return jsonify({'message': f'Error al obtener mapeos de listas-canales: {str(e)}'}), 500

@card_channel_bp.route('/mapping/<mapping_id>', methods=['DELETE'])
@token_required
def delete_list_channel_mapping(current_user_id, mapping_id):
    """
    Elimina un mapeo de lista-canal por su ID
    """
    try:
        if not mapping_id or mapping_id == 'None' or mapping_id == 'undefined' or mapping_id == 'null' or mapping_id.strip() == '':
            current_app.logger.warning(f"Intento de eliminar mapeo con ID inválido: {mapping_id}")
            return jsonify({'message': 'ID de mapeo no válido'}), 400
        try:
            mapping_object_id = ObjectId(mapping_id)
        except Exception as e:
            current_app.logger.warning(f"Error al convertir ID de mapeo a ObjectId: {mapping_id}, Error: {e}")
            return jsonify({'message': f'ID de mapeo con formato inválido: {mapping_id}'}), 400
        db = current_app.config['MONGO_DB']
        mapping = db.card_channel_mappings.find_one({'_id': mapping_object_id})
        if not mapping:
            current_app.logger.warning(f"Mapeo no encontrado con ID: {mapping_id}")
            return jsonify({'message': 'Mapeo no encontrado'}), 404
        integration = db.integrations.find_one({
            '_id': mapping['integration_id'],
            'created_by': ObjectId(current_user_id)
        })
        if not integration:
            current_app.logger.warning(f"Usuario {current_user_id} no autorizado para eliminar el mapeo {mapping_id}")
            return jsonify({'message': 'No autorizado para eliminar este mapeo'}), 403
        delete_result = db.card_channel_mappings.delete_one({'_id': mapping_object_id})
        if delete_result.deleted_count == 0:
            current_app.logger.error(f"Error al eliminar mapeo: no se eliminó ningún documento con ID {mapping_id}")
            return jsonify({'message': 'No se pudo eliminar el mapeo'}), 500
        current_app.logger.info(f"Mapeo {mapping_id} eliminado exitosamente por el usuario {current_user_id}")
        return jsonify({'message': 'Mapeo eliminado exitosamente'}), 200
    except Exception as e:
        current_app.logger.error(f"Error al eliminar mapeo de lista-canal: {e}")
        return jsonify({'message': f'Error al eliminar mapeo de lista-canal: {str(e)}'}), 500

@card_channel_bp.route('/create-direct', methods=['POST'])
@token_required
def create_direct_mapping(current_user_id):
    """
    Crear un mapeo directo entre una tarjeta de Trello y un canal de Discord
    """
    # Obtener datos del JSON
    data = request.get_json()
    
    # Verificar que existan todos los campos necesarios
    required_fields = ['integration_id', 'trello_card_id', 'trello_card_name', 'discord_channel_id', 'discord_channel_name']
    for field in required_fields:
        if field not in data or not data[field]:
            current_app.logger.warning(f"Campo requerido faltante: {field}")
            return jsonify({'error': f'El campo {field} es requerido'}), 400
    
    integration_id = data.get('integration_id')
    trello_card_id = data.get('trello_card_id')
    trello_card_name = data.get('trello_card_name')
    discord_channel_id = data.get('discord_channel_id')
    discord_channel_name = data.get('discord_channel_name')
    
    # Validar IDs
    try:
        integration_id_obj = ObjectId(integration_id)
    except:
        current_app.logger.warning(f"ID de integración inválido: {integration_id}")
        return jsonify({'error': 'ID de integración inválido'}), 400
    
    try:
        current_user_id_obj = ObjectId(current_user_id)
    except:
        current_app.logger.warning(f"ID de usuario inválido: {current_user_id}")
        return jsonify({'error': 'ID de usuario inválido'}), 400
    
    db = current_app.config['MONGO_DB']
    
    # Verificar que la integración existe y le pertenece al usuario
    integration = db.integrations.find_one({'_id': integration_id_obj})
    if not integration:
        current_app.logger.warning(f"No se encontró la integración con ID: {integration_id}")
        return jsonify({'error': 'No se encontró la integración'}), 404
    
    if integration.get('created_by') != current_user_id_obj:
        current_app.logger.warning(f"Usuario {current_user_id} intenta acceder a integración que no le pertenece: {integration_id}")
        return jsonify({'error': 'No tienes permiso para esta integración'}), 403
    
    # Verificar si ya existe un mapeo para esta tarjeta
    existing_card_mapping = db.card_channel_mappings.find_one({
        'integration_id': integration_id_obj,
        'trello_card_id': trello_card_id
    })
    
    if existing_card_mapping:
        return jsonify({
            'warning': 'Ya existe un mapeo para esta tarjeta de Trello',
            'mapping_id': str(existing_card_mapping['_id'])
        }), 200
    
    # Verificar si ya existe un mapeo para este canal
    existing_channel_mapping = db.card_channel_mappings.find_one({
        'integration_id': integration_id_obj,
        'discord_channel_id': discord_channel_id
    })
    
    if existing_channel_mapping:
        return jsonify({
            'warning': 'Ya existe un mapeo para este canal de Discord',
            'mapping_id': str(existing_channel_mapping['_id'])
        }), 200
    
    # Crear un nuevo mapeo
    try:
        mapping = CardChannelMapping(
            trello_card_id=trello_card_id,
            trello_card_name=trello_card_name,
            discord_channel_id=discord_channel_id,
            discord_channel_name=discord_channel_name,
            integration_id=integration_id_obj,  # Ya convertido a ObjectId
            created_by=current_user_id_obj,     # Ya convertido a ObjectId
            created_automatically=False
        )
        
        # Convertir a diccionario para MongoDB
        try:
            mapping_dict = mapping.to_dict()
        except ValueError as e:
            current_app.logger.error(f"Error al convertir mapeo a diccionario: {e}")
            return jsonify({'error': f'Error al crear el mapeo: {str(e)}'}), 400
        
        # Insertar en la base de datos
        result = db.card_channel_mappings.insert_one(mapping_dict)
        if not result.inserted_id:
            current_app.logger.error(f"Error al crear mapeo directo: ID generado inválido: {result.inserted_id}")
            return jsonify({'error': 'Error al crear el mapeo en la base de datos'}), 500
        
        mapping_id = result.inserted_id
        
        # Intentar enviar mensaje a Discord
        try:
            current_app.logger.info(f"Intentando enviar mensaje a Discord para el mapeo: {mapping_id}")
            
            # Enviar mensaje a Discord usando el servicio existente
            message_content = f"**Tarjeta de Trello vinculada manualmente: {trello_card_name}**\n\n"
            message_content += f"Esta tarjeta ha sido vinculada directamente a este canal."
            
            message = get_discord_service().send_message_sync(
                discord_channel_id,
                message_content
            )
            
            # Actualizar el mapeo con el ID del mensaje si se pudo enviar
            if message and 'id' in message:
                db.card_channel_mappings.update_one(
                    {'_id': mapping_id},
                    {'$set': {'discord_message_id': message['id']}}
                )
                current_app.logger.info(f"Mensaje enviado a Discord con éxito: {message['id']}")
            else:
                current_app.logger.warning(f"No se pudo enviar mensaje a Discord para el mapeo: {mapping_id}")
                
        except Exception as e:
            current_app.logger.error(f"Error al enviar mensaje a Discord: {e}")
            # No retornamos error, continuamos con el proceso
        
        current_app.logger.info(f"Mapeo directo creado con éxito: {mapping_id}")
        return jsonify({
            'message': 'Mapeo creado con éxito',
            'mapping_id': str(mapping_id)
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error al crear mapeo directo: {e}")
        return jsonify({'error': f'Error al crear el mapeo: {str(e)}'}), 500 