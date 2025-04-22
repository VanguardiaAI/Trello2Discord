from datetime import datetime
from bson import ObjectId

class Integration:
    """
    Modelo para la integración entre Trello y Discord
    """
    def __init__(self, **kwargs):
        self._id = kwargs.get('_id', None)
        self.trello_board_id = kwargs.get('trello_board_id', '')
        self.discord_server_id = kwargs.get('discord_server_id', '')
        self.webhook_id = kwargs.get('webhook_id', '')
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())
        self.created_by = kwargs.get('created_by', None)  # ID del usuario que creó la integración
        self.active = kwargs.get('active', True)
        # Campos adicionales para el polling
        self.last_check = kwargs.get('last_check', None)
        self.trello_board_name = kwargs.get('trello_board_name', '')
        self.trello_board_url = kwargs.get('trello_board_url', '')
        self.polling_interval = kwargs.get('polling_interval', 300)  # 5 minutos por defecto

    def to_dict(self):
        """
        Convierte el objeto a un diccionario para almacenar en MongoDB
        """
        return {
            '_id': self._id,
            'trello_board_id': self.trello_board_id,
            'discord_server_id': self.discord_server_id,
            'webhook_id': self.webhook_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'created_by': self.created_by,
            'active': self.active,
            'last_check': self.last_check,
            'trello_board_name': self.trello_board_name,
            'trello_board_url': self.trello_board_url,
            'polling_interval': self.polling_interval
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Crea una instancia de Integration a partir de un diccionario
        """
        return cls(**data) 