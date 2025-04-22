import os
import discord
import asyncio
import threading
from discord.ext import commands
from app import app

class DiscordService:
    """
    Servicio para interactuar con la API de Discord
    """
    def __init__(self):
        """
        Inicializa el cliente de Discord con las credenciales de la aplicación
        """
        self.token = os.environ.get('DISCORD_BOT_TOKEN')
        
        if not self.token:
            raise ValueError("El token del bot de Discord no está configurado")
        
        # Cliente de Discord
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        
        self.bot = commands.Bot(command_prefix='!', intents=intents)
        self.loop = asyncio.new_event_loop()
        
        # Iniciar el bot en un hilo separado
        self._start_bot_thread()
    
    def _start_bot_thread(self):
        """
        Inicia el bot de Discord en un hilo separado
        """
        def run_bot():
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.bot.start(self.token))
        
        thread = threading.Thread(target=run_bot)
        thread.daemon = True
        thread.start()
    
    async def get_guild(self, guild_id):
        """
        Obtiene un servidor de Discord por su ID
        """
        try:
            return await self.bot.fetch_guild(int(guild_id))
        except Exception as e:
            app.logger.error(f"Error al obtener el servidor de Discord: {e}")
            return None
    
    def get_guild_sync(self, guild_id):
        """
        Versión sincrónica de get_guild
        """
        future = asyncio.run_coroutine_threadsafe(
            self.get_guild(guild_id), self.loop
        )
        return future.result()
    
    async def get_guild_members(self, guild_id):
        """
        Obtiene los miembros de un servidor de Discord
        """
        try:
            guild = await self.get_guild(guild_id)
            if not guild:
                return []
            
            members = []
            async for member in guild.fetch_members():
                if not member.bot:
                    members.append({
                        'id': str(member.id),
                        'username': member.name,
                        'discriminator': member.discriminator,
                        'display_name': member.display_name
                    })
            
            return members
        except Exception as e:
            app.logger.error(f"Error al obtener los miembros del servidor de Discord: {e}")
            return []
    
    def get_guild_members_sync(self, guild_id):
        """
        Versión sincrónica de get_guild_members
        """
        future = asyncio.run_coroutine_threadsafe(
            self.get_guild_members(guild_id), self.loop
        )
        return future.result()
    
    async def create_channel(self, guild_id, channel_name):
        """
        Crea un canal de texto en un servidor de Discord
        """
        try:
            guild = await self.get_guild(guild_id)
            if not guild:
                return None
            
            # Sanitizar el nombre del canal (solo letras, números, guiones y guiones bajos)
            import re
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '-', channel_name.lower())
            
            # Crear el canal
            channel = await guild.create_text_channel(safe_name)
            
            return {
                'id': str(channel.id),
                'name': channel.name
            }
        except Exception as e:
            app.logger.error(f"Error al crear el canal de Discord: {e}")
            return None
    
    def create_channel_sync(self, guild_id, channel_name):
        """
        Versión sincrónica de create_channel
        """
        future = asyncio.run_coroutine_threadsafe(
            self.create_channel(guild_id, channel_name), self.loop
        )
        return future.result()
    
    async def send_message(self, channel_id, content, mention_user_id=None):
        """
        Envía un mensaje a un canal de Discord
        """
        try:
            channel = await self.bot.fetch_channel(int(channel_id))
            
            if mention_user_id:
                content = f"<@{mention_user_id}> {content}"
            
            message = await channel.send(content)
            
            return {
                'id': str(message.id),
                'content': message.content
            }
        except Exception as e:
            app.logger.error(f"Error al enviar el mensaje a Discord: {e}")
            return None
    
    def send_message_sync(self, channel_id, content, mention_user_id=None):
        """
        Versión sincrónica de send_message
        """
        future = asyncio.run_coroutine_threadsafe(
            self.send_message(channel_id, content, mention_user_id), self.loop
        )
        return future.result()
    
    async def get_channels(self, guild_id):
        """
        Obtiene los canales de texto de un servidor de Discord
        """
        try:
            guild = await self.get_guild(guild_id)
            if not guild:
                return []
            
            channels = []
            for channel in await guild.fetch_channels():
                if isinstance(channel, discord.TextChannel):
                    channels.append({
                        'id': str(channel.id),
                        'name': channel.name
                    })
            
            return channels
        except Exception as e:
            app.logger.error(f"Error al obtener los canales de Discord: {e}")
            return []
    
    def get_channels_sync(self, guild_id):
        """
        Versión sincrónica de get_channels
        """
        future = asyncio.run_coroutine_threadsafe(
            self.get_channels(guild_id), self.loop
        )
        return future.result() 