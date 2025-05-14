# Script con instrucciones para la búsqueda de leads mejorada
# Este script NO inicia servidores automáticamente

# Colores para los mensajes
$Green = @{ForegroundColor = "Green"}
$Yellow = @{ForegroundColor = "Yellow"}
$Red = @{ForegroundColor = "Red"}
$Cyan = @{ForegroundColor = "Cyan"}

Write-Host "Información sobre la búsqueda de leads mejorada" @Cyan
Write-Host "===============================================" @Cyan

Write-Host "`nCambios implementados:" @Green
Write-Host "✓ Mejorado el endpoint '/places/niche-suggestions' para gestionar acentos y tildes"
Write-Host "✓ Añadido soporte para búsqueda en plural/singular ('clínica estética'/'clínicas estéticas')"
Write-Host "✓ Reducido el número mínimo de caracteres para búsqueda de 3 a 2"
Write-Host "✓ Agregado mejor manejo de normalización de texto (sin tildes/acentos)"

Write-Host "`nCómo iniciar los servidores manualmente:" @Yellow
Write-Host "1. Para el backend: Abre una terminal y ejecuta:"
Write-Host "   cd server"
Write-Host "   venv\Scripts\activate"
Write-Host "   python run.py"
Write-Host "2. Para el frontend: Abre otra terminal y ejecuta:"
Write-Host "   cd client"
Write-Host "   npm run dev"

Write-Host "`nPara probar la búsqueda de nichos:" @Cyan
Write-Host "1. Abre la aplicación en el navegador (http://localhost:5173)" 
Write-Host "2. Ve a la pestaña 'Buscar Leads'" 
Write-Host "3. Selecciona el modo 'Búsqueda por tipo de negocio'"
Write-Host "4. Escribe 'clínica' o 'clinica' (con o sin acento) y verás sugerencias de:"
Write-Host "   - Clínica estética"
Write-Host "   - Clínicas estéticas"
Write-Host "   - Clínica dental"
Write-Host "   - Clínica veterinaria"
Write-Host "   - etc."
Write-Host "5. Las categorías ahora aparecen correctamente aunque escribas sin acentos"
Write-Host "6. Ingresa una dirección y realiza la búsqueda" 