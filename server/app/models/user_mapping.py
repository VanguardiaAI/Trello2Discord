from datetime import datetime
from bson import ObjectId

class UserMapping:
    """
    Modelo para mapear usuarios de Trello a usuarios de Discord
    """
    def __init__(self, **kwargs):
        self._id = kwargs.get('_id', None)
        self.trello_user_id = kwargs.get('trello_user_id', '')
        self.trello_username = kwargs.get('trello_username', '')
        self.discord_user_id = kwargs.get('discord_user_id', '')
        self.discord_username = kwargs.get('discord_username', '')
        self.integration_id = kwargs.get('integration_id', None)  # ID de la integración a la que pertenece
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())
        self.created_by = kwargs.get('created_by', None)  # ID del usuario que creó el mapeo

    def to_dict(self):
        """
        Convierte el objeto a un diccionario para almacenar en MongoDB
        """
        return {
            '_id': self._id,
            'trello_user_id': self.trello_user_id,
            'trello_username': self.trello_username,
            'discord_user_id': self.discord_user_id,
            'discord_username': self.discord_username,
            'integration_id': self.integration_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'created_by': self.created_by
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Crea una instancia de UserMapping a partir de un diccionario
        """
        return cls(**data) 