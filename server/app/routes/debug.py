from flask import Blueprint, jsonify, current_app, request
from app.routes.integration import get_trello_service
import requests
import os
import threading
import time
from datetime import datetime, timedelta
import json
from app.discord.bot import send_message_to_channel, create_discord_channel, send_message_with_button
from app.models.user_mapping import UserMapping
from app.models.card_channel_mapping import CardChannelMapping
import re
from app.services.discord_service import DiscordService

debug_bp = Blueprint('debug', __name__)

# Variable global para almacenar el estado anterior de las tarjetas
previous_cards_state = {}
# Variable para controlar el hilo de polling
polling_active = False
# ID del tablero de Trello que estamos monitoreando
monitored_board_id = None

# Estado global para listas y tarjetas
previous_lists_state = {}

def format_date_spanish(date_str):
    """
    Formatea una fecha ISO 8601 en formato español: DD/MM/YYYY HH:MMhrs
    Ajustada a la hora de España peninsular (UTC+2)
    """
    if not date_str:
        return "Sin fecha"
    try:
        # Convertir la cadena ISO a objeto datetime
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        # Añadir 2 horas para ajustar a la hora de España peninsular
        date_obj = date_obj + timedelta(hours=2)
        # Formatear la fecha en formato español
        return date_obj.strftime('%d/%m/%Y %H:%M') + "hrs"
    except Exception as e:
        current_app.logger.error(f"Error al formatear fecha {date_str}: {e}")
        return date_str

def get_trello_cards(board_id):
    """
    Obtiene todas las tarjetas de un tablero específico de Trello, incluyendo adjuntos, fecha de vencimiento y etiquetas.
    """
    try:
        api_key = os.environ.get('TRELLO_API_KEY')
        token = os.environ.get('TRELLO_TOKEN')
        if not api_key or not token:
            current_app.logger.error("Credenciales de Trello no configuradas")
            return None
        cards_url = f"https://api.trello.com/1/boards/{board_id}/cards"
        headers = {"Accept": "application/json"}
        query = {
            'key': api_key,
            'token': token,
            'fields': 'id,name,desc,idList,idMembers,dateLastActivity,shortUrl,due,labels',
            'attachments': 'true',
            'attachment_fields': 'id,name,url,bytes,date',
        }
        response = requests.get(cards_url, headers=headers, params=query)
        if response.status_code != 200:
            current_app.logger.error(f"Error al obtener tarjetas: HTTP {response.status_code}")
            return None
        return response.json()
    except Exception as e:
        current_app.logger.error(f"Error en get_trello_cards: {e}")
        return None

def get_trello_member_details(member_id):
    """
    Obtiene detalles de un miembro específico de Trello
    """
    try:
        api_key = os.environ.get('TRELLO_API_KEY')
        token = os.environ.get('TRELLO_TOKEN')
        
        if not api_key or not token:
            current_app.logger.error("Credenciales de Trello no configuradas")
            return None
        
        member_url = f"https://api.trello.com/1/members/{member_id}"
        headers = {
            "Accept": "application/json"
        }
        query = {
            'key': api_key,
            'token': token,
            'fields': 'id,username,fullName'
        }
        
        response = requests.get(member_url, headers=headers, params=query)
        
        if response.status_code != 200:
            current_app.logger.error(f"Error al obtener miembro: HTTP {response.status_code}")
            return None
        
        return response.json()
    except Exception as e:
        current_app.logger.error(f"Error en get_trello_member_details: {e}")
        return None

def get_discord_user_id(trello_user_id):
    """
    Obtiene el ID de usuario de Discord mapeado a un usuario de Trello
    """
    try:
        db = current_app.config['MONGO_DB']
        
        # Buscar en la base de datos el mapeo de usuario
        user_mapping = db.user_mappings.find_one({'trello_user_id': trello_user_id})
        
        if user_mapping and 'discord_user_id' in user_mapping:
            current_app.logger.info(f"Mapeo encontrado: Usuario Trello {trello_user_id} -> Usuario Discord {user_mapping['discord_user_id']}")
            return user_mapping['discord_user_id']
        else:
            current_app.logger.info(f"No se encontró mapeo para el usuario de Trello: {trello_user_id}")
            return None
    except Exception as e:
        current_app.logger.error(f"Error al obtener mapeo de usuario: {e}")
        return None

def get_discord_channel_id(trello_card_id):
    """
    Obtiene el ID del canal de Discord mapeado a una tarjeta de Trello
    """
    try:
        db = current_app.config['MONGO_DB']
        
        # Buscar en la base de datos el mapeo de tarjeta-canal
        card_mapping = db.card_channel_mappings.find_one({'trello_card_id': trello_card_id})
        
        if card_mapping and 'discord_channel_id' in card_mapping:
            current_app.logger.info(f"Mapeo encontrado: Tarjeta Trello {trello_card_id} -> Canal Discord {card_mapping['discord_channel_id']}")
            return card_mapping['discord_channel_id']
        else:
            current_app.logger.info(f"No se encontró mapeo para la tarjeta de Trello: {trello_card_id}")
            return None
    except Exception as e:
        current_app.logger.error(f"Error al obtener mapeo de tarjeta-canal: {e}")
        return None

def save_card_channel_mapping(trello_card_id, discord_channel_id):
    """
    Guarda el mapeo entre una tarjeta de Trello y un canal de Discord
    """
    try:
        db = current_app.config['MONGO_DB']
        
        # Datos para el mapeo
        mapping_data = {
            'trello_card_id': trello_card_id,
            'discord_channel_id': discord_channel_id,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Verificar si ya existe un mapeo para esta tarjeta
        existing_mapping = db.card_channel_mappings.find_one({'trello_card_id': trello_card_id})
        
        if existing_mapping:
            # Actualizar el mapeo existente
            db.card_channel_mappings.update_one(
                {'_id': existing_mapping['_id']},
                {'$set': {
                    'discord_channel_id': discord_channel_id,
                    'updated_at': datetime.utcnow()
                }}
            )
            current_app.logger.info(f"Mapeo actualizado: Tarjeta {trello_card_id} -> Canal {discord_channel_id}")
        else:
            # Crear un nuevo mapeo
            db.card_channel_mappings.insert_one(mapping_data)
            current_app.logger.info(f"Nuevo mapeo creado: Tarjeta {trello_card_id} -> Canal {discord_channel_id}")
        
        return True
    except Exception as e:
        current_app.logger.error(f"Error al guardar mapeo de tarjeta-canal: {e}")
        return False

def get_trello_lists(board_id):
    """
    Obtiene todas las listas de un tablero específico de Trello.
    """
    try:
        api_key = os.environ.get('TRELLO_API_KEY')
        token = os.environ.get('TRELLO_TOKEN')
        if not api_key or not token:
            current_app.logger.error("Credenciales de Trello no configuradas")
            return None
        lists_url = f"https://api.trello.com/1/boards/{board_id}/lists"
        headers = {"Accept": "application/json"}
        query = {
            'key': api_key,
            'token': token,
            'fields': 'id,name,closed'
        }
        response = requests.get(lists_url, headers=headers, params=query)
        if response.status_code != 200:
            current_app.logger.error(f"Error al obtener listas: HTTP {response.status_code}")
            return None
        return response.json()
    except Exception as e:
        current_app.logger.error(f"Error en get_trello_lists: {e}")
        return None

def get_discord_channel_id_by_list(trello_list_id):
    """
    Obtiene el ID del canal de Discord mapeado a una lista de Trello
    """
    try:
        db = current_app.config['MONGO_DB']
        mapping = db.card_channel_mappings.find_one({'trello_list_id': trello_list_id})
        if mapping and 'discord_channel_id' in mapping:
            return mapping['discord_channel_id']
        return None
    except Exception as e:
        current_app.logger.error(f"Error al obtener mapeo de lista-canal: {e}")
        return None

def save_list_channel_mapping(trello_list_id, trello_list_name, discord_channel_id):
    try:
        db = current_app.config['MONGO_DB']
        mapping_data = {
            'trello_list_id': trello_list_id,
            'trello_list_name': trello_list_name,
            'discord_channel_id': str(discord_channel_id),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'created_automatically': True
        }
        existing_mapping = db.card_channel_mappings.find_one({'trello_list_id': trello_list_id})
        if existing_mapping:
            db.card_channel_mappings.update_one(
                {'_id': existing_mapping['_id']},
                {'$set': {
                    'discord_channel_id': str(discord_channel_id),
                    'updated_at': datetime.utcnow()
                }}
            )
            current_app.logger.info(f"Mapeo actualizado: Lista {trello_list_id} -> Canal {discord_channel_id}")
        else:
            db.card_channel_mappings.insert_one(mapping_data)
            current_app.logger.info(f"Nuevo mapeo creado: Lista {trello_list_id} -> Canal {discord_channel_id}")
        return True
    except Exception as e:
        current_app.logger.error(f"Error al guardar mapeo de lista-canal: {e}")
        return False

def detect_and_process_trello_changes():
    """
    Detecta cambios en listas y tarjetas de Trello y realiza las acciones correspondientes.
    """
    global previous_lists_state, previous_cards_state, polling_active, monitored_board_id
    from flask import current_app
    if not monitored_board_id:
        current_app.logger.info("No hay tablero configurado para monitorear")
        print("No hay tablero configurado para monitorear")
        return
    try:
        current_app.logger.info(f"Verificando cambios en el tablero {monitored_board_id}")
        print(f"Verificando cambios en el tablero {monitored_board_id}")
        # Obtener estado actual de listas y tarjetas
        current_lists = get_trello_lists(monitored_board_id)
        current_cards = get_trello_cards(monitored_board_id)
        if not current_lists or not current_cards:
            current_app.logger.warning("No se pudieron obtener listas o tarjetas actuales")
            print("No se pudieron obtener listas o tarjetas actuales")
            return
        current_lists_dict = {lst['id']: lst for lst in current_lists if not lst.get('closed', False)}
        current_cards_dict = {card['id']: card for card in current_cards}
        # --- PRIMERA EJECUCIÓN ---
        if not previous_lists_state or not previous_cards_state:
            previous_lists_state = current_lists_dict
            previous_cards_state = current_cards_dict
            print(f"Estado inicial almacenado: {len(current_lists_dict)} listas, {len(current_cards_dict)} tarjetas")
            return
        # --- DETECTAR NUEVAS LISTAS ---
        for list_id, lst in current_lists_dict.items():
            if list_id not in previous_lists_state:
                current_app.logger.info(f"Nueva lista detectada: {lst['name']} (ID: {list_id})")
                print(f"Nueva lista detectada: {lst['name']} (ID: {list_id})")
                # Obtener integración para el board actual
                db = current_app.config['MONGO_DB']
                integration = db.integrations.find_one({'trello_board_id': monitored_board_id})
                if not integration or 'discord_server_id' not in integration:
                    current_app.logger.error("No se encontró la integración o el discord_server_id para este board")
                    print("No se encontró la integración o el discord_server_id para este board")
                    continue
                guild_id = integration['discord_server_id']
                # Crear canal de Discord y mapear
                channel_name = f"{lst['name'].lower().replace(' ', '-')[:90]}"
                safe_name = re.sub(r'[^a-zA-Z0-9_-]', '-', channel_name)
                current_app.logger.info(f"Intentando crear canal de Discord: {safe_name} en servidor {guild_id}")
                discord_channel_id = create_discord_channel(safe_name, guild_id)
                if discord_channel_id:
                    current_app.logger.info(f"Canal de Discord creado exitosamente: {discord_channel_id}")
                    save_list_channel_mapping(list_id, lst['name'], discord_channel_id)
                else:
                    current_app.logger.error(f"ERROR: No se pudo crear canal de Discord para la lista {list_id}")
                    print(f"ERROR: No se pudo crear canal de Discord para la lista {list_id}")
        # --- DETECTAR NUEVAS TARJETAS Y ACTUALIZACIONES ---
        for card_id, card in current_cards_dict.items():
            if card_id not in previous_cards_state:
                current_app.logger.info(f"Nueva tarjeta detectada: {card['name']} (ID: {card_id})")
                print(f"Nueva tarjeta detectada: {card['name']} (ID: {card_id})")
                process_new_card_list_based(card)
            else:
                if card.get('dateLastActivity') != previous_cards_state[card_id].get('dateLastActivity'):
                    current_app.logger.info(f"Tarjeta actualizada: {card['name']} (ID: {card_id})")
                    print(f"Tarjeta actualizada: {card['name']} (ID: {card_id})")
                    process_updated_card_list_based(previous_cards_state[card_id], card)
        # Actualizar estado
        previous_lists_state = current_lists_dict
        previous_cards_state = current_cards_dict
    except Exception as e:
        print(f"Error en detect_and_process_trello_changes: {e}")
        import traceback
        print(traceback.format_exc())

def process_new_card_list_based(card):
    """
    Envía mensaje de asignación al canal de la lista correspondiente cuando se crea una nueva tarjeta y se asigna a un miembro.
    """
    try:
        trello_list_id = card.get('idList')
        discord_channel_id = get_discord_channel_id_by_list(trello_list_id)
        if not discord_channel_id:
            print(f"No se encontró canal de Discord para la lista {trello_list_id}")
            return
        # Si la tarjeta tiene asignados, enviar mensaje con botón de confirmación
        assigned_discord_users = [get_discord_user_id(mid) for mid in card.get('idMembers', []) if get_discord_user_id(mid)]
        if assigned_discord_users:
            for member_id in card['idMembers']:
                discord_user_id = get_discord_user_id(member_id)
                if discord_user_id:
                    confirmation_message = (
                        f"📄 **Tarea:** {card['name']}\n"
                    )
                    if card.get('desc'):
                        confirmation_message += f"📝 **Descripción:** {card.get('desc')}\n"
                    if card.get('due'):
                        fecha_formateada = format_date_spanish(card.get('due'))
                        confirmation_message += f"📅 **Fecha límite:** {fecha_formateada}\n"
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
                        discord_channel_id,
                        confirmation_message,
                        "Confirmar asignación",
                        card['id'],
                        discord_user_id,
                        "confirm"
                    )
        else:
            # Si no hay asignados, solo enviar mensaje informativo
            message = f"**Nueva tarjeta creada en Trello**\n"
            message += f"📄 **Tarea:** {card['name']}\n"
            if card.get('desc'):
                message += f"📝 **Descripción:** {card.get('desc')}\n"
            if card.get('due'):
                fecha_formateada = format_date_spanish(card.get('due'))
                message += f"📅 **Fecha límite:** {fecha_formateada}\n"
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
            send_message_to_channel(discord_channel_id, message)
        print(f"Mensaje de nueva tarjeta enviado al canal de la lista {trello_list_id}")
    except Exception as e:
        print(f"ERROR en process_new_card_list_based: {e}")
        import traceback
        print(traceback.format_exc())

def process_updated_card_list_based(old_card, new_card):
    """
    Envía mensaje de actualización al canal de la lista correspondiente cuando una tarjeta es actualizada.
    """
    try:
        trello_list_id = new_card.get('idList')
        discord_channel_id = get_discord_channel_id_by_list(trello_list_id)
        if not discord_channel_id:
            print(f"No se encontró canal de Discord para la lista {trello_list_id}")
            return
        cambios = []
        if old_card.get('name', '') != new_card.get('name', ''):
            cambios.append(f"📄 *Título cambiado:* '{old_card.get('name', '')}' → '{new_card.get('name', '')}'")
        if old_card.get('desc', '') != new_card.get('desc', ''):
            nueva_desc = new_card.get('desc', '').strip()
            if nueva_desc:
                cambios.append(f"⚠️ *Descripción actualizada para tarea '{new_card.get('name')}':* {nueva_desc}")
            else:
                cambios.append(f"⚠️ *Descripción eliminada para tarea '{new_card.get('name')}'*")
        if old_card.get('due') != new_card.get('due'):
            old_due_fmt = format_date_spanish(old_card.get('due')) if old_card.get('due') else 'Sin fecha'
            new_due_fmt = format_date_spanish(new_card.get('due')) if new_card.get('due') else 'Sin fecha'
            cambios.append(f"📅 *Fecha límite cambiada para la tarea '{new_card.get('name')}':* '{old_due_fmt}' → '{new_due_fmt}'")
        old_labels = set(label.get('name', '') for label in old_card.get('labels', []) if label.get('name'))
        new_labels = set(label.get('name', '') for label in new_card.get('labels', []) if label.get('name'))
        added_labels = new_labels - old_labels
        removed_labels = old_labels - new_labels
        if added_labels:
            cambios.append(f"🏷️ *Etiqueta añadida para tarea '{new_card.get('name')}':* {', '.join(added_labels)}")
        if removed_labels:
            cambios.append(f"🏷️ *Etiqueta eliminada para tarea '{new_card.get('name')}':* {', '.join(removed_labels)}")
        old_attachments = set((a.get('id'), a.get('name')) for a in old_card.get('attachments', []))
        new_attachments = set((a.get('id'), a.get('name')) for a in new_card.get('attachments', []))
        added_attachments = new_attachments - old_attachments
        removed_attachments = old_attachments - new_attachments
        if added_attachments:
            cambios.append(f"📎 *Adjunto añadido para tarea '{new_card.get('name')}':*\n" + '\n'.join(f"- {name}" for (_id, name) in added_attachments))
        if removed_attachments:
            cambios.append(f"📎 *Adjunto eliminado para tarea '{new_card.get('name')}':*\n" + '\n'.join(f"- {name}" for (_id, name) in removed_attachments))
        old_members = set(old_card.get('idMembers', []))
        new_members = set(new_card.get('idMembers', []))
        nuevos_asignados = new_members - old_members
        removidos = old_members - new_members
        if cambios or nuevos_asignados or removidos:
            message = ""
            if cambios:
                message += "\n".join(cambios) + "\n"
            for member_id in nuevos_asignados:
                trello_member = get_trello_member_details(member_id)
                discord_user_id = get_discord_user_id(member_id)
                if discord_user_id:
                    confirmation_message = (
                        f"📄 **Tarea:** {new_card['name']}\n"
                    )
                    if new_card.get('desc'):
                        confirmation_message += f"📝 **Descripción:** {new_card.get('desc')}\n"
                    if new_card.get('due'):
                        fecha_formateada = format_date_spanish(new_card.get('due'))
                        confirmation_message += f"📅 **Fecha límite:** {fecha_formateada}\n"
                    if new_card.get('labels'):
                        etiquetas = ', '.join([label.get('name', '') for label in new_card.get('labels', []) if label.get('name')])
                        if etiquetas:
                            confirmation_message += f"🏷️ **Etiquetas:** {etiquetas}\n"
                    if new_card.get('attachments'):
                        adjuntos = new_card['attachments']
                        if adjuntos:
                            confirmation_message += "📎 **Adjuntos:**\n"
                            for adj in adjuntos:
                                confirmation_message += f"- {adj.get('name', 'Archivo')}\n"
                    confirmation_message += f"🙋‍♂️ **Asignado a:** <@{discord_user_id}>\n"
                    if new_card.get('shortUrl'):
                        confirmation_message += f"\n📌 **Enlace a la tarjeta:** {new_card.get('shortUrl')}\n"
                    confirmation_message += "\nPor favor, confirma que vista esta asignación haciendo clic en el botón:"
                    send_message_with_button(
                        discord_channel_id,
                        confirmation_message,
                        "Confirmar asignación",
                        new_card['id'],
                        discord_user_id,
                        "confirm"
                    )
                else:
                    if trello_member:
                        message += f"🙋‍♂️ Nuevo asignado: {trello_member.get('fullName', 'Desconocido')} (no mapeado a Discord)\n"
            for member_id in removidos:
                trello_member = get_trello_member_details(member_id)
                if trello_member:
                    message += f"🙋‍♂️ Ya no asignado: {trello_member.get('fullName', 'Desconocido')}\n"
            message = message.strip()
            if message:
                print(f"Enviando mensaje de actualización al canal {discord_channel_id}")
                send_message_to_channel(discord_channel_id, message)
        else:
            print("No se detectaron cambios significativos. No se enviará mensaje general.")
        print(f"Procesamiento de tarjeta actualizada completado: {new_card['id']}")
    except Exception as e:
        print(f"ERROR en process_updated_card_list_based: {e}")
        import traceback
        print(traceback.format_exc())

def polling_thread(app=None):
    """
    Función que se ejecuta en un hilo separado para realizar el polling de Trello
    """
    global polling_active
    
    if app is None:
        print("ERROR: No se proporcionó la instancia de la aplicación al hilo de polling")
        return
    
    print(f"Iniciando hilo de polling de Trello con app={app}")
    
    while polling_active:
        try:
            # Con aplicación Flask como contexto
            with app.app_context():
                detect_and_process_trello_changes()
        except Exception as e:
            # Capturar cualquier excepción para evitar que el hilo se detenga
            print(f"Error en el hilo de polling: {e}")
            import traceback
            print(traceback.format_exc())
        
        # Esperar 10 segundos antes de la siguiente verificación
        time.sleep(10)
    
    print("Hilo de polling de Trello detenido")

@debug_bp.route('/trello/start-monitoring/<board_id>', methods=['POST'])
def start_monitoring(board_id):
    """
    Inicia el monitoreo de un tablero específico de Trello
    """
    global polling_active, monitored_board_id
    
    if polling_active:
        return jsonify({
            'status': 'warning',
            'message': 'El monitoreo ya está activo. Detén el monitoreo actual antes de iniciar uno nuevo.'
        }), 400
    
    try:
        # Verificar que el tablero existe
        api_key = os.environ.get('TRELLO_API_KEY')
        token = os.environ.get('TRELLO_TOKEN')
        
        if not api_key or not token:
            return jsonify({
                'status': 'error',
                'message': 'Credenciales de Trello no configuradas'
            }), 400
        
        # Intentar obtener el tablero para verificar que existe
        board_url = f"https://api.trello.com/1/boards/{board_id}"
        headers = {"Accept": "application/json"}
        query = {'key': api_key, 'token': token}
        
        response = requests.get(board_url, headers=headers, params=query)
        
        if response.status_code != 200:
            return jsonify({
                'status': 'error',
                'message': f'Error al obtener el tablero: HTTP {response.status_code}',
                'details': response.text
            }), 400
        
        # El tablero existe, iniciar el monitoreo
        monitored_board_id = board_id
        polling_active = True
        
        # Obtener la instancia de la aplicación actual para pasarla al hilo
        app = current_app._get_current_object()
        
        # Iniciar el hilo de polling pasando la aplicación
        polling_thread_instance = threading.Thread(target=polling_thread, args=(app,))
        polling_thread_instance.daemon = True  # El hilo se cerrará cuando el programa principal termine
        polling_thread_instance.start()
        
        # Esperar 1 segundo para asegurarse de que el hilo inicie correctamente
        time.sleep(1)
        
        return jsonify({
            'status': 'success',
            'message': f'Monitoreo iniciado para el tablero {board_id}',
            'board_name': response.json().get('name', 'Tablero desconocido')
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error al iniciar el monitoreo: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error al iniciar el monitoreo: {str(e)}'
        }), 500

@debug_bp.route('/trello/stop-monitoring', methods=['POST'])
def stop_monitoring():
    """
    Detiene el monitoreo de Trello
    """
    global polling_active, monitored_board_id
    
    if not polling_active:
        return jsonify({
            'status': 'warning',
            'message': 'No hay monitoreo activo para detener'
        }), 400
    
    try:
        # Detener el hilo de polling
        polling_active = False
        monitored_board_id = None
        
        return jsonify({
            'status': 'success',
            'message': 'Monitoreo detenido correctamente'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error al detener el monitoreo: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error al detener el monitoreo: {str(e)}'
        }), 500

@debug_bp.route('/trello/monitoring-status', methods=['GET'])
def monitoring_status():
    """
    Obtiene el estado actual del monitoreo
    """
    global polling_active, monitored_board_id
    
    return jsonify({
        'status': 'success',
        'active': polling_active,
        'monitored_board_id': monitored_board_id
    }), 200

# Rutas originales de debug.py
@debug_bp.route('/trello/check-credentials', methods=['GET'])
def check_trello_credentials():
    """
    Verifica que las credenciales de Trello son válidas
    """
    try:
        # Intentar inicializar el servicio de Trello
        trello_service = get_trello_service()
        
        # Si llega aquí, las credenciales son válidas
        return jsonify({
            'status': 'success',
            'message': 'Credenciales de Trello válidas',
            'api_key': trello_service.api_key[:5] + '...',  # Solo mostrar parte de la clave por seguridad
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error al verificar credenciales de Trello: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error al verificar credenciales de Trello: {str(e)}'
        }), 500

@debug_bp.route('/trello/boards', methods=['GET'])
def get_boards():
    """
    Obtiene todos los tableros disponibles para el usuario de Trello
    """
    try:
        # Obtener credenciales directamente
        api_key = os.environ.get('TRELLO_API_KEY')
        token = os.environ.get('TRELLO_TOKEN')
        
        if not api_key or not token:
            return jsonify({
                'status': 'error',
                'message': 'Credenciales de Trello no configuradas'
            }), 400
        
        # Hacer solicitud HTTP directa en lugar de usar la biblioteca py-trello
        url = "https://api.trello.com/1/members/me/boards"
        headers = {
            "Accept": "application/json"
        }
        query = {
            'key': api_key,
            'token': token,
            'fields': 'id,name,url,closed,desc'
        }
        
        response = requests.get(url, headers=headers, params=query)
        
        if response.status_code != 200:
            current_app.logger.error(f"Error al obtener tableros de Trello: {response.text}")
            return jsonify({
                'status': 'error',
                'message': f'Error al obtener tableros: HTTP {response.status_code}',
                'details': response.text
            }), 500
        
        # Procesar la respuesta
        all_boards = response.json()
        
        # Formatear la respuesta
        boards = []
        for board in all_boards:
            boards.append({
                'id': board.get('id'),
                'name': board.get('name'),
                'url': board.get('url'),
                'closed': board.get('closed', False),
                'description': board.get('desc', '')
            })
        
        return jsonify({
            'status': 'success',
            'count': len(boards),
            'boards': boards
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error al obtener tableros de Trello: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error al obtener tableros de Trello: {str(e)}'
        }), 500

@debug_bp.route('/trello/board/<board_id>/details', methods=['GET'])
def get_board_details(board_id):
    """
    Obtiene detalles específicos de un tablero, incluyendo listas y miembros
    """
    try:
        # Obtener credenciales directamente
        api_key = os.environ.get('TRELLO_API_KEY')
        token = os.environ.get('TRELLO_TOKEN')
        
        if not api_key or not token:
            return jsonify({
                'status': 'error',
                'message': 'Credenciales de Trello no configuradas'
            }), 400
        
        # Hacer solicitud HTTP para obtener detalles del tablero
        board_url = f"https://api.trello.com/1/boards/{board_id}"
        headers = {
            "Accept": "application/json"
        }
        query = {
            'key': api_key,
            'token': token,
            'fields': 'id,name,url,desc'
        }
        
        board_response = requests.get(board_url, headers=headers, params=query)
        
        if board_response.status_code != 200:
            current_app.logger.error(f"Error al obtener el tablero {board_id}: {board_response.text}")
            return jsonify({
                'status': 'error',
                'message': f'Error al obtener el tablero: HTTP {board_response.status_code}',
                'details': board_response.text
            }), 500
        
        board_data = board_response.json()
        
        # Obtener listas del tablero
        lists_url = f"https://api.trello.com/1/boards/{board_id}/lists"
        lists_query = {
            'key': api_key,
            'token': token,
            'fields': 'id,name,closed'
        }
        
        lists_response = requests.get(lists_url, headers=headers, params=lists_query)
        
        if lists_response.status_code != 200:
            current_app.logger.error(f"Error al obtener listas del tablero {board_id}: {lists_response.text}")
            return jsonify({
                'status': 'error',
                'message': f'Error al obtener listas del tablero: HTTP {lists_response.status_code}',
                'details': lists_response.text
            }), 500
        
        lists_data = lists_response.json()
        
        # Obtener miembros del tablero
        members_url = f"https://api.trello.com/1/boards/{board_id}/members"
        members_query = {
            'key': api_key,
            'token': token,
            'fields': 'id,username,fullName'
        }
        
        members_response = requests.get(members_url, headers=headers, params=members_query)
        
        if members_response.status_code != 200:
            current_app.logger.error(f"Error al obtener miembros del tablero {board_id}: {members_response.text}")
            return jsonify({
                'status': 'error',
                'message': f'Error al obtener miembros del tablero: HTTP {members_response.status_code}',
                'details': members_response.text
            }), 500
        
        members_data = members_response.json()
        
        # Formatear la respuesta
        lists = []
        for lst in lists_data:
            lists.append({
                'id': lst.get('id'),
                'name': lst.get('name'),
                'closed': lst.get('closed', False)
            })
        
        members = []
        for member in members_data:
            members.append({
                'id': member.get('id'),
                'username': member.get('username'),
                'full_name': member.get('fullName')
            })
        
        return jsonify({
            'status': 'success',
            'board': {
                'id': board_data.get('id'),
                'name': board_data.get('name'),
                'url': board_data.get('url'),
                'description': board_data.get('desc', '')
            },
            'lists': lists,
            'members': members
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error al obtener detalles del tablero {board_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error al obtener detalles del tablero: {str(e)}'
        }), 500

@debug_bp.route('/trello/board/<board_id>/cards', methods=['GET'])
def get_board_cards(board_id):
    """
    Obtiene todas las tarjetas de un tablero específico
    """
    try:
        # Obtener credenciales directamente
        api_key = os.environ.get('TRELLO_API_KEY')
        token = os.environ.get('TRELLO_TOKEN')
        
        if not api_key or not token:
            return jsonify({
                'status': 'error',
                'message': 'Credenciales de Trello no configuradas'
            }), 400
        
        # Hacer solicitud HTTP para obtener tarjetas del tablero
        cards_url = f"https://api.trello.com/1/boards/{board_id}/cards"
        headers = {
            "Accept": "application/json"
        }
        query = {
            'key': api_key,
            'token': token,
            'fields': 'id,name,desc,url,shortUrl,closed,idList,idBoard,due,labels'
        }
        
        response = requests.get(cards_url, headers=headers, params=query)
        
        if response.status_code != 200:
            current_app.logger.error(f"Error al obtener tarjetas del tablero {board_id}: {response.text}")
            return jsonify({
                'status': 'error',
                'message': f'Error al obtener tarjetas: HTTP {response.status_code}',
                'details': response.text
            }), 500
        
        cards_data = response.json()
        
        if not cards_data:
            return jsonify({
                'status': 'success',
                'message': 'No se encontraron tarjetas en este tablero',
                'cards': []
            }), 200
        
        # Formatear la respuesta
        formatted_cards = []
        for card in cards_data:
            formatted_cards.append({
                'id': card.get('id'),
                'name': card.get('name'),
                'description': card.get('desc', ''),
                'url': card.get('url'),
                'short_url': card.get('shortUrl'),
                'closed': card.get('closed', False),
                'id_list': card.get('idList'),
                'id_board': card.get('idBoard'),
                'due': card.get('due'),
                'labels': [{'id': label.get('id'), 'name': label.get('name', ''), 'color': label.get('color', '')} 
                          for label in card.get('labels', [])]
            })
        
        return jsonify({
            'status': 'success',
            'count': len(formatted_cards),
            'cards': formatted_cards
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error al obtener tarjetas del tablero {board_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error al obtener tarjetas del tablero: {str(e)}'
        }), 500

@debug_bp.route('/trello/check-credentials-detailed', methods=['GET'])
def check_trello_credentials_detailed():
    """
    Verifica las credenciales de Trello con información detallada para diagnóstico
    """
    api_key = os.environ.get('TRELLO_API_KEY')
    token = os.environ.get('TRELLO_TOKEN')
    
    # Verificar si las credenciales están presentes
    if not api_key or not token:
        return jsonify({
            'status': 'error',
            'message': 'Credenciales de Trello no configuradas',
            'api_key_present': bool(api_key),
            'token_present': bool(token)
        }), 400
    
    # Intentar hacer una solicitud directa a la API
    try:
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
                'message': 'Credenciales de Trello válidas',
                'user_info': {
                    'id': user_data.get('id'),
                    'username': user_data.get('username'),
                    'fullName': user_data.get('fullName'),
                    'email': user_data.get('email')
                },
                'api_key': api_key[:5] + '...',
                'token': token[:5] + '...',
            }), 200
        else:
            return jsonify({
                'status': 'error',
                'message': f'Error al verificar credenciales: HTTP {response.status_code}',
                'response_text': response.text,
                'api_key': api_key[:5] + '...',
                'token': token[:5] + '...',
            }), 400
    except Exception as e:
        current_app.logger.error(f"Error al verificar credenciales de Trello detalladas: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error al conectar con Trello: {str(e)}',
            'api_key': api_key[:5] + '...',
            'token': token[:5] + '...',
        }), 500 