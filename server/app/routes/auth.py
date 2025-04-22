from flask import Blueprint, request, jsonify, current_app
import jwt
from datetime import datetime, timedelta
from app.models.user import User
import traceback
from functools import wraps

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'No se recibieron datos en formato JSON'}), 400
    
    # Validación de contraseña 
    if data.get('temp_password') != 'Workana2025':
        return jsonify({'success': False, 'message': 'Contraseña incorrecta'}), 403
    
    # Validación de datos
    if not data.get('email'):
        return jsonify({'success': False, 'message': 'El correo electrónico es obligatorio'}), 400
    if not data.get('password'):
        return jsonify({'success': False, 'message': 'La contraseña es obligatoria'}), 400
    if not data.get('name'):
        return jsonify({'success': False, 'message': 'El nombre es obligatorio'}), 400
    
    # Verificar si el usuario ya existe
    db = current_app.config['MONGO_DB']
    existing_user = User.find_by_email(data['email'], db)
    
    if existing_user:
        return jsonify({'success': False, 'message': 'El correo electrónico ya está registrado'}), 409
    
    # Crear nuevo usuario
    try:
        user = User(
            name=data['name'],
            email=data['email'],
            password=data['password']
        )
        user.save(db)
        
        return jsonify({
            'success': True, 
            'message': 'Usuario registrado con éxito',
            'user': user.to_dict()
        }), 201
    except Exception as e:
        print(f"Error al registrar usuario: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error al registrar usuario. Inténtalo de nuevo.'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'No se recibieron datos en formato JSON'}), 400
    
    # Validación de datos
    if not data.get('email'):
        return jsonify({'success': False, 'message': 'El correo electrónico es obligatorio'}), 400
    if not data.get('password'):
        return jsonify({'success': False, 'message': 'La contraseña es obligatoria'}), 400
    
    try:
        # Buscar usuario por email
        db = current_app.config['MONGO_DB']
        user = User.find_by_email(data['email'], db)
        
        if not user:
            return jsonify({'success': False, 'message': 'El correo electrónico no está registrado'}), 401
        
        if not user.check_password(data['password']):
            return jsonify({'success': False, 'message': 'Contraseña incorrecta'}), 401
        
        # Generar token JWT
        token_expiry = datetime.utcnow() + timedelta(days=7)  # Token válido por 7 días
        token_payload = {
            'sub': str(user._id),
            'name': user.name,
            'email': user.email,
            'exp': token_expiry
        }
        
        token = jwt.encode(
            token_payload, 
            current_app.config['JWT_SECRET_KEY'],
            algorithm='HS256'
        )
        
        return jsonify({
            'success': True,
            'message': 'Inicio de sesión exitoso',
            'token': token,
            'user': user.to_dict(),
            'expiresAt': token_expiry.isoformat()
        }), 200
    
    except Exception as e:
        print(f"Error en login: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error al iniciar sesión. Inténtalo de nuevo.'}), 500

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    # Obtener token de cabecera Authorization
    auth_header = request.headers.get('Authorization')
    
    if not auth_header:
        return jsonify({'success': False, 'message': 'No se proporcionó token de autenticación'}), 401
    
    if not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'message': 'Formato de token inválido. Usa Bearer {token}'}), 401
    
    token = auth_header.split(' ')[1]
    
    try:
        # Decodificar token
        jwt_data = jwt.decode(
            token, 
            current_app.config['JWT_SECRET_KEY'],
            algorithms=['HS256']
        )
        
        # Buscar usuario por ID
        db = current_app.config['MONGO_DB']
        user = User.find_by_id(jwt_data['sub'], db)
        
        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        }), 200
    except jwt.ExpiredSignatureError:
        return jsonify({'success': False, 'message': 'Token expirado. Inicia sesión nuevamente.'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'success': False, 'message': 'Token inválido. Inicia sesión nuevamente.'}), 401
    except Exception as e:
        print(f"Error al obtener usuario actual: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': 'Error al validar la sesión'}), 500 

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            token = auth_header.split(" ")[1] if len(auth_header.split(" ")) > 1 else None
        if not token:
            return jsonify({'message': 'Token no proporcionado'}), 401
        try:
            data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            current_user_id = data['sub']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expirado. Inicia sesión nuevamente.'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token inválido. Inicia sesión nuevamente.'}), 401
        except Exception as e:
            current_app.logger.error(f"Error al verificar token: {e}")
            return jsonify({'message': 'Error al validar la sesión'}), 401
        return f(current_user_id, *args, **kwargs)
    return decorated

@auth_bp.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user_id):
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No se recibieron datos en formato JSON'}), 400
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    if not current_password or not new_password:
        return jsonify({'success': False, 'message': 'Debes proporcionar la contraseña actual y la nueva contraseña'}), 400
    db = current_app.config['MONGO_DB']
    user = User.find_by_id(current_user_id, db)
    if not user:
        return jsonify({'success': False, 'message': 'Usuario no encontrado'}), 404
    if not user.check_password(current_password):
        return jsonify({'success': False, 'message': 'La contraseña actual es incorrecta'}), 401
    # Actualizar la contraseña
    user.password = user._hash_password(new_password)
    user.save(db)
    return jsonify({'success': True, 'message': 'Contraseña actualizada correctamente'}), 200 