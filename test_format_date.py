from datetime import datetime, timedelta
import os
import sys

# Vamos a definir la función directamente para evitar problemas de importación
def format_date_spanish(date_str):
    """
    Formatea una fecha ISO 8601 en formato español: DD/MM/YYYY HH:MMhrs
    Ajustada a la hora de España peninsular (UTC+2)
    """
    if not date_str:
        return "Sin fecha"
    try:
        # Convertir la cadena ISO a objeto datetime
        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        # Añadir 2 horas para ajustar a la hora de España peninsular
        date_obj = date_obj + timedelta(hours=2)
        # Formatear la fecha en formato español
        return date_obj.strftime('%d/%m/%Y %H:%M') + "hrs"
    except Exception as e:
        print(f"Error al formatear fecha {date_str}: {e}")
        return date_str

# Fechas de prueba
test_dates = [
    "2023-05-22T15:00:00Z",              # Formato UTC
    "2023-05-22T15:00:00+00:00",         # Formato ISO con zona horaria explícita
    "2023-05-22T15:00:00",               # Sin zona horaria
    datetime.utcnow().isoformat() + "Z"  # Fecha actual en UTC
]

print("\n======= PRUEBA DE CONVERSIÓN DE FECHAS =======")
print("Verificando la conversión de fechas a formato español con ajuste de zona horaria")
print("La hora en España peninsular debería ser UTC+2\n")

for date_str in test_dates:
    print(f"Fecha original: {date_str}")
    
    # Mostrar la fecha parseada sin ajustes
    try:
        date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        print(f"Fecha parseada (UTC): {date_obj.strftime('%d/%m/%Y %H:%M')}")
    except Exception as e:
        print(f"Error al parsear sin ajustes: {e}")
    
    # Usar nuestra función
    formatted = format_date_spanish(date_str)
    print(f"Resultado de format_date_spanish: {formatted}")
    
    # Cálculo manual para comparar
    try:
        date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        date_obj_plus2 = date_obj + timedelta(hours=2)
        manual_format = date_obj_plus2.strftime('%d/%m/%Y %H:%M') + "hrs"
        print(f"Cálculo manual (UTC+2): {manual_format}")
        
        if formatted == manual_format:
            print("✅ Los resultados coinciden")
        else:
            print("❌ Los resultados NO coinciden")
    except Exception as e:
        print(f"Error en cálculo manual: {e}")
    
    print("-" * 50)

print("\nResumen de la zona horaria del sistema:")
print(f"Zona horaria actual: {datetime.now().astimezone().tzinfo}")
print(f"Hora UTC actual: {datetime.utcnow().strftime('%H:%M:%S')}")
print(f"Hora local actual: {datetime.now().strftime('%H:%M:%S')}")
print(f"Diferencia aproximada: {(datetime.now() - datetime.utcnow()).total_seconds() / 3600:.1f} horas") 