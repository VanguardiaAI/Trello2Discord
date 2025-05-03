from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import os
from pymongo import MongoClient
from dotenv import load_dotenv
import certifi
import json
from bson import ObjectId
from datetime import datetime, timedelta
import logging

load_dotenv()

app = Flask(__name__)
# Configuración mejorada de CORS
CORS(app, resources={r"/api/*": {"origins": os.environ.get('FRONTEND_ORIGIN', "http://localhost:5173"), "supports_credentials": True}}, 
     allow_headers=["Content-Type", "Authorization"], 
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])

# Configurar logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# Clase personalizada para JSON encoder para MongoDB
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

app.json_encoder = CustomJSONEncoder

# Configuración de secretos
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'clavedesarrollo123'
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY') or 'jwtsecretkey123'

# Configuración JWT
app.config['JWT_TOKEN_LOCATION'] = ['headers']
app.config['JWT_HEADER_NAME'] = 'Authorization'
app.config['JWT_HEADER_TYPE'] = 'Bearer'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# Inicializar JWT Manager
jwt = JWTManager(app)

# Conexión a MongoDB Atlas
mongo_uri = os.environ.get('MONGO_URI')
try:
    # Usar certificado SSL para conexión segura
    client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
    # Obtener base de datos específica o usar la que está en la URI
    db_name = os.environ.get('DB_NAME') or 'boilerplate'
    db = client[db_name]
    # Verificar la conexión
    client.admin.command('ping')
    app.config['MONGO_DB'] = db
    print(f"Conexión a MongoDB Atlas exitosa. Base de datos: {db_name}")
except Exception as e:
    print(f"Error al conectar a MongoDB Atlas: {e}")
    raise

# Importación y registro de blueprints
from app.routes.auth import auth_bp
app.register_blueprint(auth_bp, url_prefix='/api/auth')

# Registrar blueprints de la aplicación Trello-Discord
from app.routes.integration import integration_bp
from app.routes.user_mapping import user_mapping_bp
from app.routes.card_channel import card_channel_bp
from app.routes.webhook import webhook_bp
from app.routes.debug import debug_bp
# Nuevos blueprints para Leads y Places
from app.routes.leads import leads_bp
from app.routes.places import places_bp

app.register_blueprint(integration_bp, url_prefix='/api/integration')
app.register_blueprint(user_mapping_bp, url_prefix='/api/user-mapping')
app.register_blueprint(card_channel_bp, url_prefix='/api/card-channel')
app.register_blueprint(webhook_bp, url_prefix='/api/webhook')
app.register_blueprint(debug_bp, url_prefix='/api/debug')
# Registrar nuevos blueprints
app.register_blueprint(leads_bp, url_prefix='/api')
app.register_blueprint(places_bp, url_prefix='/api')

# Eliminar el bloque if __name__ == '__main__': para evitar ejecución en modo debug en producción 