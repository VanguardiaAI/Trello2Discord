import os
import discord
from discord.ext import commands
import logging
from discord import ButtonStyle, Interaction
from discord.ui import Button, View
from app import app  # Importar la instancia de Flask

# Configurar logger
logger = logging.getLogger(__name__)

# Token del bot de Discord
DISCORD_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')

# Cliente de Discord
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
bot.remove_command('help')  # Quitar comando de ayuda por defecto

# Variable para rastrear si el bot está inicializado
bot_initialized = False

# Diccionario para almacenar información sobre interacciones de botones
button_callbacks = {}

def init_discord_bot():
    """
    Inicializa el bot de Discord si no está ya inicializado
    """
    global bot_initialized
    
    if bot_initialized:
        return True
    
    if not DISCORD_TOKEN:
        logger.error("Token de Discord no configurado")
        return False
    
    try:
        # Iniciar el bot en un hilo separado
        import threading
        
        def run_bot():
            bot.run(DISCORD_TOKEN)
        
        bot_thread = threading.Thread(target=run_bot)
        bot_thread.daemon = True
        bot_thread.start()
        
        # Consideramos el bot como inicializado
        bot_initialized = True
        
        @bot.event
        async def on_ready():
            """Evento que se ejecuta cuando el bot está listo"""
            logger.info(f"Bot conectado como {bot.user.name}")
            logger.info(f"Bot está en los siguientes servidores: {[g.name for g in bot.guilds]}")
        
        @bot.event
        async def on_interaction(interaction: Interaction):
            """Manejador de interacciones con botones"""
            # Verificar si la interacción es con un botón
            if interaction.type == discord.InteractionType.component:
                custom_id = interaction.data.get("custom_id", "")
                logger.info(f"[Discord] Botón presionado. custom_id={custom_id}, usuario={interaction.user.id}")
                
                # Verificar si tenemos un callback registrado para este botón
                if custom_id in button_callbacks:
                    callback_data = button_callbacks[custom_id]
                    logger.info(f"[Discord] Callback encontrado para custom_id={custom_id}: {callback_data}")
                    
                    # Extraer la información necesaria
                    trello_card_id = callback_data.get("trello_card_id")
                    user_id = callback_data.get("user_id")
                    action = callback_data.get("action")
                    logger.info(f"[Discord] Intentando actualizar Trello: card_id={trello_card_id}, user_id={user_id}, action={action}")
                    
                    # Responder a la interacción
                    await interaction.response.send_message(
                        f"Confirmación recibida. Actualizando tarjeta en Trello...",
                        ephemeral=True
                    )
                    
                    # Importar la función para actualizar Trello
                    from app.routes.integration import update_trello_card_with_confirmation
                    
                    try:
                        with app.app_context():
                            result = update_trello_card_with_confirmation(trello_card_id, user_id, action)
                        logger.info(f"[Discord] Resultado de update_trello_card_with_confirmation: {result}")
                    except Exception as e:
                        logger.error(f"[Discord] Excepción al llamar a update_trello_card_with_confirmation: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        result = False
                    
                    # Informar sobre el resultado
                    if result:
                        # Editar el mensaje original para mostrar quién confirmó
                        try:
                            original_message = await interaction.original_message()
                            new_content = original_message.content + f"\n\n✅ Confirmado por <@{interaction.user.id}>"
                            
                            # Crear una nueva vista sin botones para el mensaje actualizado
                            await interaction.message.edit(content=new_content, view=None)
                            logger.info(f"[Discord] Mensaje editado correctamente tras confirmación.")
                            
                            # Nos aseguramos de que el separador siga presente debajo del mensaje
                            # No necesitamos enviar un nuevo separador porque ya existe uno después de cada mensaje con botón
                            
                            # Eliminar el callback ya que ha sido utilizado
                            del button_callbacks[custom_id]
                        except Exception as e:
                            logger.error(f"[Discord] Error al actualizar el mensaje original: {e}")
                    else:
                        # Informar sobre el error
                        await interaction.followup.send(
                            "Hubo un problema al actualizar la tarjeta en Trello.",
                            ephemeral=True
                        )
                        logger.error(f"[Discord] Fallo al actualizar Trello para card_id={trello_card_id}, user_id={user_id}")
        
        return True
    except Exception as e:
        logger.error(f"Error al inicializar el bot de Discord: {e}")
        return False

async def _create_discord_channel_async(channel_name, guild_id):
    """
    Crea un nuevo canal de texto en Discord (versión asíncrona)
    """
    logger = logging.getLogger("app.discord.bot")
    logger.info(f"[DEPURACIÓN] Intentando crear canal: '{channel_name}' en guild: {guild_id}")
    if not bot_initialized:
        if not init_discord_bot():
            logger.error("No se pudo inicializar el bot de Discord")
            return None
    import asyncio
    count = 0
    guild = None
    while not guild and count < 30:
        guild = bot.get_guild(int(guild_id))
        if not guild:
            await asyncio.sleep(1)
            count += 1
    if not guild:
        logger.error(f"No se pudo obtener el servidor de Discord con ID {guild_id}")
        return None
    try:
        logger.info(f"[DEPURACIÓN] Llamando a create_text_channel con nombre: '{channel_name}' en guild: {guild_id}")
        channel = await guild.create_text_channel(channel_name)
        logger.info(f"[DEPURACIÓN] Resultado de create_text_channel: {channel} (ID: {getattr(channel, 'id', None)})")
        logger.info(f"Canal de Discord creado: {channel.name} (ID: {channel.id})")
        return channel.id
    except Exception as e:
        logger.error(f"Error al crear canal en Discord: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def create_discord_channel(channel_name, guild_id):
    """
    Función no asíncrona para crear un canal en Discord
    Esta función se puede llamar desde el código sincrónico
    """
    if not bot_initialized:
        if not init_discord_bot():
            logger.error("No se pudo inicializar el bot de Discord")
            return None
    
    # Planificar la creación del canal en el bucle de eventos de asyncio del bot
    import asyncio
    future = asyncio.run_coroutine_threadsafe(_create_discord_channel_async(channel_name, guild_id), bot.loop)
    
    try:
        # Esperar el resultado con un timeout
        return future.result(timeout=30)  # 30 segundos de timeout
    except asyncio.TimeoutError:
        logger.error("Timeout al crear canal en Discord")
        return None
    except Exception as e:
        logger.error(f"Error al crear canal en Discord desde hilo principal: {e}")
        return None

async def _send_message_async(channel_id, message):
    """
    Envía un mensaje a un canal específico (versión asíncrona)
    """
    if not bot_initialized:
        if not init_discord_bot():
            logger.error("No se pudo inicializar el bot de Discord")
            return False
    
    try:
        # Obtener el canal
        channel = bot.get_channel(int(channel_id))
        
        if not channel:
            logger.error(f"No se pudo encontrar el canal con ID: {channel_id}")
            return False
        
        # Enviar el mensaje
        await channel.send(message)
        logger.info(f"Mensaje enviado al canal {channel.name} (ID: {channel_id})")
        return True
    except discord.Forbidden:
        logger.error(f"No tengo permisos para enviar mensajes al canal {channel_id}")
        return False
    except discord.HTTPException as e:
        logger.error(f"Error HTTP al enviar mensaje a Discord: {e}")
        return False
    except Exception as e:
        logger.error(f"Error al enviar mensaje a Discord: {e}")
        return False

def send_message_to_channel(channel_id, message):
    """
    Función no asíncrona para enviar un mensaje a un canal de Discord
    Esta función se puede llamar desde el código sincrónico
    """
    if not bot_initialized:
        if not init_discord_bot():
            logger.error("No se pudo inicializar el bot de Discord")
            return False
    
    # Planificar el envío del mensaje en el bucle de eventos de asyncio del bot
    import asyncio
    future = asyncio.run_coroutine_threadsafe(_send_message_async(channel_id, message), bot.loop)
    
    try:
        # Esperar el resultado con un timeout
        return future.result(timeout=30)  # 30 segundos de timeout
    except asyncio.TimeoutError:
        logger.error("Timeout al enviar mensaje a Discord")
        return False
    except Exception as e:
        logger.error(f"Error al enviar mensaje a Discord desde hilo principal: {e}")
        return False

async def _send_message_with_button_async(channel_id, message, button_label, trello_card_id, user_id, action="confirm"):
    """
    Envía un mensaje con un botón interactivo (versión asíncrona)
    """
    if not bot_initialized:
        if not init_discord_bot():
            logger.error("No se pudo inicializar el bot de Discord")
            return False
    
    try:
        # Obtener el canal
        channel = bot.get_channel(int(channel_id))
        
        if not channel:
            logger.error(f"No se pudo encontrar el canal con ID: {channel_id}")
            return False
        
        # Crear un ID único para el botón
        import uuid
        button_id = f"confirm_{uuid.uuid4()}"
        
        # Registrar el callback para este botón
        button_callbacks[button_id] = {
            "trello_card_id": trello_card_id,
            "user_id": user_id,
            "action": action
        }
        
        # Crear el botón
        button = Button(style=ButtonStyle.primary, label=button_label, custom_id=button_id)
        
        # Crear la vista con el botón
        view = View(timeout=None)
        view.add_item(button)
        
        # Enviar el mensaje con el botón
        await channel.send(message, view=view)
        logger.info(f"Mensaje con botón enviado al canal {channel.name} (ID: {channel_id})")
        
        # Enviar separador después del mensaje con botón
        await channel.send("───────────────────────────────────────")
        logger.info(f"Separador enviado después del mensaje con botón al canal {channel.name} (ID: {channel_id})")
        
        return True
    except discord.Forbidden:
        logger.error(f"No tengo permisos para enviar mensajes al canal {channel_id}")
        return False
    except discord.HTTPException as e:
        logger.error(f"Error HTTP al enviar mensaje a Discord: {e}")
        return False
    except Exception as e:
        logger.error(f"Error al enviar mensaje con botón a Discord: {e}")
        return False

def send_message_with_button(channel_id, message, button_label, trello_card_id, user_id, action="confirm"):
    """
    Función no asíncrona para enviar un mensaje con botón a un canal de Discord
    Esta función se puede llamar desde el código sincrónico
    """
    if not bot_initialized:
        if not init_discord_bot():
            logger.error("No se pudo inicializar el bot de Discord")
            return False
    
    # Planificar el envío del mensaje en el bucle de eventos de asyncio del bot
    import asyncio
    future = asyncio.run_coroutine_threadsafe(
        _send_message_with_button_async(channel_id, message, button_label, trello_card_id, user_id, action),
        bot.loop
    )
    
    try:
        # Esperar el resultado con un timeout
        return future.result(timeout=30)  # 30 segundos de timeout
    except asyncio.TimeoutError:
        logger.error("Timeout al enviar mensaje con botón a Discord")
        return False
    except Exception as e:
        logger.error(f"Error al enviar mensaje con botón a Discord desde hilo principal: {e}")
        return False

# Inicializar el bot al importar el módulo
init_discord_bot() 

