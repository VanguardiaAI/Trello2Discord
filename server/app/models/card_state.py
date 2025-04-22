from datetime import datetime
from bson import ObjectId

class CardState:
    """
    Modelo para almacenar el estado de una tarjeta de Trello
    para poder detectar cambios durante el polling
    """
    def __init__(self, **kwargs):
        self._id = kwargs.get('_id', None)
        self.integration_id = kwargs.get('integration_id', None)
        self.card_id = kwargs.get('card_id', '')
        self.name = kwargs.get('name', '')
        self.id_list = kwargs.get('id_list', '')
        self.description = kwargs.get('description', '')
        self.last_modified = kwargs.get('last_modified', datetime.utcnow())
        self.is_processed = kwargs.get('is_processed', False)
        self.labels = kwargs.get('labels', [])
        self.due = kwargs.get('due', None)

    def to_dict(self):
        """
        Convierte el objeto a un diccionario para almacenar en MongoDB
        """
        return {
            '_id': self._id,
            'integration_id': self.integration_id,
            'card_id': self.card_id,
            'name': self.name,
            'id_list': self.id_list,
            'description': self.description,
            'last_modified': self.last_modified,
            'is_processed': self.is_processed,
            'labels': self.labels,
            'due': self.due
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Crea una instancia de CardState a partir de un diccionario
        """
        return cls(**data) 