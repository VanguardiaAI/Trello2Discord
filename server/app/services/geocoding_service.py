import requests
import os
from dotenv import load_dotenv

load_dotenv()

GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
API_KEY = os.getenv("GOOGLE_PLACES_API_KEY")

if not API_KEY:
    raise ValueError("La API KEY de Google Places no está configurada en el archivo .env")

def geocode_address(address):
    params = {
        "address": address,
        "key": API_KEY
    }
    response = requests.get(GEOCODING_URL, params=params)
    data = response.json()
    if data.get("status") != "OK":
        error_message = data.get("error_message", "No se pudo geocodificar la dirección")
        raise Exception(f"Error en la API de Geocoding: {error_message}")
    result = data["results"][0]
    location = result["geometry"]["location"]
    return {
        "lat": location["lat"],
        "lng": location["lng"],
        "formatted_address": result["formatted_address"]
    } 