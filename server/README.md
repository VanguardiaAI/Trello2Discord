# Backend de Autenticación con Flask y MongoDB

Este es el backend para la aplicación de autenticación, desarrollado con Flask y MongoDB Atlas.

## Requisitos

- Python 3.7+
- pip (administrador de paquetes de Python)
- MongoDB Atlas (cuenta y cluster configurado)

## Configuración

1. Crea un entorno virtual:

```bash
python -m venv venv
```

2. Activa el entorno virtual:

En Windows:
```bash
venv\Scripts\activate
```

En macOS/Linux:
```bash
source venv/bin/activate
```

3. Instala las dependencias:

```bash
pip install -r requirements.txt
```

4. Configura las variables de entorno:

El archivo `.env` ya contiene la configuración necesaria para conectarse a MongoDB Atlas. Si necesitas cambiar la configuración, edita el archivo `.env`:

```
SECRET_KEY=tu_clave_secreta
JWT_SECRET_KEY=tu_clave_jwt
MONGO_URI=tu_uri_de_mongodb_atlas
```

## Ejecución

Para iniciar el servidor:

```bash
python run.py
```

El servidor se iniciará en `http://localhost:5000`.

## Rutas disponibles

### Autenticación

- `POST /api/auth/register`: Registro de usuario
  - Cuerpo: `{ "name": "Nombre", "email": "correo@ejemplo.com", "password": "contraseña" }`
  - Respuesta: `{ "success": true, "message": "Usuario registrado con éxito", "user": {...} }`

- `POST /api/auth/login`: Inicio de sesión
  - Cuerpo: `{ "email": "correo@ejemplo.com", "password": "contraseña" }`
  - Respuesta: `{ "success": true, "message": "Inicio de sesión exitoso", "token": "...", "user": {...}, "expiresAt": "..." }`

- `GET /api/auth/me`: Obtener información del usuario actual
  - Cabecera: `Authorization: Bearer tu_token`
  - Respuesta: `{ "success": true, "user": {...} }`

## Estructura del proyecto

- `app/`: Directorio principal de la aplicación
  - `__init__.py`: Inicialización de la aplicación Flask
  - `models/`: Modelos de datos
    - `user.py`: Modelo de usuario
  - `routes/`: Rutas de la API
    - `auth.py`: Rutas de autenticación
- `run.py`: Script para ejecutar la aplicación
- `requirements.txt`: Dependencias del proyecto
- `.env`: Variables de entorno

# Despliegue en Producción

## Backend (Flask)

1. Instala waitress:

```
pip install waitress
```

2. Asegúrate de tener todas las variables de entorno configuradas (usa el archivo .env.example como referencia, pero NO lo subas a producción).

3. Ejecuta el backend con waitress:

```
waitress-serve --host=0.0.0.0 --port=5000 app:app
```

## Frontend (React/Vite)

1. Configura las variables de entorno en `client/.env.production`.
2. Genera el build de producción:

```
npm run build
```

3. Sube el contenido de la carpeta `dist/` a tu servidor web o CDN.

## Seguridad y buenas prácticas
- Cambia todas las claves y tokens antes de desplegar.
- Usa HTTPS en producción.
- Limita los orígenes permitidos en CORS.
- No expongas endpoints de debug en producción.
- No subas archivos `.env` reales al repositorio. 