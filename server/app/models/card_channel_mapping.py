from datetime import datetime
from bson import ObjectId

class CardChannelMapping:
    """
    Modelo para mapear tarjetas de Trello a canales de Discord
    """
    def __init__(self, **kwargs):
        self._id = kwargs.get('_id', None)
        self.trello_card_id = kwargs.get('trello_card_id', '')
        self.trello_card_name = kwargs.get('trello_card_name', '')
        self.discord_channel_id = kwargs.get('discord_channel_id', '')
        self.discord_channel_name = kwargs.get('discord_channel_name', '')
        self.integration_id = kwargs.get('integration_id', None)  # ID de la integración a la que pertenece
        self.trello_member_id = kwargs.get('trello_member_id', None)  # ID del miembro de Trello asignado
        self.discord_message_id = kwargs.get('discord_message_id', None)  # ID del mensaje inicial en Discord
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())
        self.created_by = kwargs.get('created_by', None)  # ID del usuario que creó el mapeo
        self.created_automatically = kwargs.get('created_automatically', True)  # Si fue creado automáticamente o manualmente

    def to_dict(self):
        """
        Convierte el objeto a un diccionario para almacenar en MongoDB
        """
        data = {
            'trello_card_id': self.trello_card_id,
            'trello_card_name': self.trello_card_name,
            'discord_channel_id': self.discord_channel_id,
            'discord_channel_name': self.discord_channel_name,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'created_automatically': self.created_automatically
        }
        
        # Verificación de validez para integration_id (obligatorio)
        if self.integration_id:
            if isinstance(self.integration_id, ObjectId):
                data['integration_id'] = self.integration_id
            else:
                try:
                    # Intentar convertir a ObjectId si es string
                    data['integration_id'] = ObjectId(str(self.integration_id))
                except Exception as e:
                    # En caso de error, registrar pero mantener el integration_id como estaba
                    # ya que es un campo obligatorio, no lo establecemos como None
                    print(f"Error al convertir integration_id a ObjectId: {e}")
                    # Si no podemos convertirlo a ObjectId, es un error crítico
                    # El código que llama debe manejar esta situación
                    raise ValueError(f"integration_id inválido: {self.integration_id}")
        else:
            # Si integration_id es None, es un error crítico
            raise ValueError("integration_id es obligatorio y no puede ser None")
        
        # Agregar campos opcionales solo si no son None
        if self._id:
            if isinstance(self._id, ObjectId):
                data['_id'] = self._id
            else:
                try:
                    data['_id'] = ObjectId(str(self._id))
                except:
                    # _id puede ser None para nuevos documentos
                    pass
            
        if self.trello_member_id:
            data['trello_member_id'] = self.trello_member_id
            
        if self.discord_message_id:
            data['discord_message_id'] = self.discord_message_id
            
        if self.created_by:
            if isinstance(self.created_by, ObjectId):
                data['created_by'] = self.created_by
            else:
                try:
                    data['created_by'] = ObjectId(str(self.created_by))
                except Exception as e:
                    print(f"Error al convertir created_by a ObjectId: {e}")
                    # created_by es importante pero no crítico
                    # usamos None para indicar que hubo un problema
                    data['created_by'] = None
        
        return data
    
    @classmethod
    def from_dict(cls, data):
        """
        Crea una instancia de CardChannelMapping a partir de un diccionario
        """
        return cls(**data) 