from app import app
import os

if __name__ == '__main__':
    # Configurar host y puerto
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() in ('true', '1', 't')
    
    print(f"Iniciando servidor en http://{host}:{port}")
    print(f"Modo debug: {debug}")
    print("Presiona CTRL+C para detener el servidor")
    
    # Ejecutar la aplicación
    app.run(host=host, port=port, debug=debug) 