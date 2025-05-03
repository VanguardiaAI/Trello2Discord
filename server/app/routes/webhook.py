from flask import Blueprint, request, jsonify, current_app
from bson.objectid import ObjectId
import re
from app.models.card_channel_mapping import CardChannelMapping
from app.routes.integration import get_discord_service, get_trello_service

webhook_bp = Blueprint('webhook', __name__)

@webhook_bp.route('/trello', methods=['POST'])
def trello_webhook():
    """
    Recibe y procesa los webhooks de Trello
    """
    try:
        data = request.json
        
        # Verificar si el webhook es para una tarjeta y una acción que nos interese
        if not data or 'action' not in data or 'model' not in data:
            return jsonify({'message': 'Webhook recibido pero sin datos relevantes'}), 200
        
        action = data['action']
        
        # Solo procesar acciones de creación o asignación de tarjetas
        if action['type'] not in ['createCard', 'updateCard', 'addMemberToCard']:
            return jsonify({'message': f"Acción {action['type']} no procesada"}), 200
        
        # Obtener la tarjeta y el tablero
        card_id = None
        board_id = None
        member_id = None
        
        # Extraer información según el tipo de acción
        if action['type'] == 'createCard':
            card_id = action['data']['card']['id']
            board_id = action['data']['board']['id']
        elif action['type'] == 'updateCard':
            card_id = action['data']['card']['id']
            board_id = action['data']['board']['id']
            # Verificar si la actualización es una asignación de miembro
            if 'idMembers' in action['data']['old'] and 'idMembers' in action['data']['card']:
                old_members = set(action['data']['old'].get('idMembers', []))
                new_members = set(action['data']['card'].get('idMembers', []))
                # Si se añadió un nuevo miembro
                added_members = new_members - old_members
                if added_members:
                    member_id = list(added_members)[0]
        elif action['type'] == 'addMemberToCard':
            card_id = action['data']['card']['id']
            board_id = action['data']['board']['id']
            member_id = action['data']['member']['id']
        
        if not card_id or not board_id:
            return jsonify({'message': 'Datos insuficientes para procesar el webhook'}), 200
        
        # Buscar la integración para este tablero
        db = current_app.config['MONGO_DB']
        integration = db.integrations.find_one({'trello_board_id': board_id})
        
        if not integration:
            return jsonify({'message': 'No existe integración para este tablero'}), 200
        
        # Verificar si ya existe un mapeo para esta tarjeta
        existing_mapping = db.card_channel_mappings.find_one({
            'trello_card_id': card_id,
            'integration_id': integration['_id']
        })
        
        if existing_mapping:
            # Si la tarjeta ya tiene un canal asociado, no hacemos nada
            return jsonify({'message': 'La tarjeta ya tiene un canal asociado'}), 200
        
        # Obtener detalles de la tarjeta
        card_details = get_trello_service().get_card(card_id)
        
        if not card_details:
            return jsonify({'message': 'No se pudo obtener información de la tarjeta'}), 200
        
        # Sanitizar el nombre de la tarjeta para usarlo como nombre del canal
        card_name = card_details['name']
        card_desc = card_details.get('desc', '')
        card_url = card_details['url']
        
        # Si tenemos un miembro asignado, buscar su mapeo en Discord
        discord_user_id = None
        if member_id:
            user_mapping = db.user_mappings.find_one({
                'trello_user_id': member_id,
                'integration_id': integration['_id']
            })
            
            if user_mapping:
                discord_user_id = user_mapping['discord_user_id']
        
        # Crear un canal en Discord
        channel_name = f"{card_id[-4:]}-{re.sub(r'[^a-zA-Z0-9]', '-', card_name.lower())}"
        channel = get_discord_service().create_channel_sync(
            integration['discord_server_id'],
            channel_name[:32]  # Discord tiene un límite de 32 caracteres para nombres de canales
        )
        
        if not channel:
            return jsonify({'message': 'No se pudo crear el canal en Discord'}), 200
        
        # Enviar mensaje al canal con información de la tarjeta
        message_content = f"**Nueva tarea de Trello: {card_name}**\n\n"
        if card_desc:
            message_content += f"Descripción: {card_desc}\n\n"
        message_content += f"Enlace: {card_url}"
        
        message = get_discord_service().send_message_sync(
            channel['id'],
            message_content,
            discord_user_id
        )
        
        # Guardar el mapeo entre la tarjeta y el canal
        card_channel_mapping = CardChannelMapping(
            trello_card_id=card_id,
            trello_card_name=card_name,
            discord_channel_id=channel['id'],
            discord_channel_name=channel['name'],
            integration_id=integration['_id'],
            trello_member_id=member_id,
            discord_message_id=message['id'] if message else None,
            created_automatically=True
        )
        
        db.card_channel_mappings.insert_one(card_channel_mapping.to_dict())
        
        return jsonify({'message': 'Webhook procesado exitosamente'}), 200
    except Exception as e:
        current_app.logger.error(f"Error al procesar webhook de Trello: {e}")
        return jsonify({'message': f'Error al procesar webhook: {str(e)}'}), 500

@webhook_bp.route('/trello', methods=['HEAD'])
def trello_webhook_head():
    """
    Responde a las solicitudes HEAD para la verificación de webhook de Trello
    """
    return '', 200 