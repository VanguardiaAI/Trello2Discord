# Aplicación de Autenticación con React, TypeScript, Flask y MongoDB

Este proyecto es una aplicación completa de autenticación con frontend en React/TypeScript y backend en Flask/MongoDB.

## Estructura del Proyecto

- `client/`: Frontend con React, TypeScript y Vite
- `server/`: Backend con Flask y MongoDB

## Requisitos

### Frontend
- Node.js
- npm

### Backend
- Python 3.7+
- MongoDB

## Configuración e Instalación

### Frontend

```bash
# Navegar al directorio del cliente
cd client

# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm run dev
```

### Backend

```bash
# Navegar al directorio del servidor
cd server

# Crear entorno virtual (Windows)
python -m venv venv
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Iniciar servidor
python run.py
```

## Características

- Registro de usuarios
- Inicio de sesión
- Autenticación con JWT
- Diseño moderno con Tailwind CSS y shadcn/ui

## Configuración del Entorno

El archivo `.env` en el directorio `server/` contiene variables de entorno para el backend:

```
SECRET_KEY=tu_clave_secreta
JWT_SECRET_KEY=tu_clave_jwt
MONGO_URI=mongodb://localhost:27017/trello2discord
```

## Licencia

MIT 