import os
import requests
from trello import TrelloClient
from app import app

class TrelloService:
    """
    Servicio para interactuar con la API de Trello
    """
    def __init__(self):
        """
        Inicializa el cliente de Trello con las credenciales de la aplicación
        """
        self.api_key = os.environ.get('TRELLO_API_KEY')
        self.token = os.environ.get('TRELLO_TOKEN')
        self.base_url = "https://api.trello.com/1"
        
        if not self.api_key or not self.token:
            raise ValueError("Las credenciales de Trello no están configuradas")
        
        # Cliente oficial de Trello
        self.client = TrelloClient(
            api_key=self.api_key,
            token=self.token
        )
    
    def get_board(self, board_id):
        """
        Obtiene un tablero de Trello por su ID
        """
        try:
            return self.client.get_board(board_id)
        except Exception as e:
            app.logger.error(f"Error al obtener el tablero de Trello: {e}")
            return None
    
    def get_board_members(self, board_id):
        """
        Obtiene los miembros de un tablero de Trello
        """
        try:
            board = self.get_board(board_id)
            if not board:
                return []
            return board.get_members()
        except Exception as e:
            app.logger.error(f"Error al obtener los miembros del tablero de Trello: {e}")
            return []
    
    def get_cards(self, board_id):
        """
        Obtiene todas las tarjetas de un tablero de Trello
        """
        try:
            board = self.get_board(board_id)
            if not board:
                return []
            
            cards = []
            for lst in board.list_lists():
                cards.extend(lst.list_cards())
            
            return cards
        except Exception as e:
            app.logger.error(f"Error al obtener las tarjetas del tablero de Trello: {e}")
            return []
    
    def create_webhook(self, board_id, callback_url):
        """
        Crea un webhook para un tablero de Trello
        """
        try:
            url = f"{self.base_url}/webhooks/"
            params = {
                'key': self.api_key,
                'token': self.token,
                'idModel': board_id,
                'callbackURL': callback_url,
                'description': 'Webhook para integración Trello-Discord',
            }
            
            response = requests.post(url, params=params)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            app.logger.error(f"Error al crear el webhook de Trello: {e}")
            return None
    
    def delete_webhook(self, webhook_id):
        """
        Elimina un webhook de Trello
        """
        try:
            url = f"{self.base_url}/webhooks/{webhook_id}"
            params = {
                'key': self.api_key,
                'token': self.token
            }
            
            response = requests.delete(url, params=params)
            response.raise_for_status()
            
            return True
        except Exception as e:
            app.logger.error(f"Error al eliminar el webhook de Trello: {e}")
            return False
    
    def get_card(self, card_id):
        """
        Obtiene una tarjeta de Trello por su ID
        """
        try:
            url = f"{self.base_url}/cards/{card_id}"
            params = {
                'key': self.api_key,
                'token': self.token
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            app.logger.error(f"Error al obtener la tarjeta de Trello: {e}")
            return None 