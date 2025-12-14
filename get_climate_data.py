import pandas as pd
import requests
import os
import yaml
from datetime import date

# CARGAR CONFIGURACIÓN
# Leemos el archivo YAML
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

# ASIGNAR VARIABLES DESDE EL CONFIG
LATITUD = config['target_city']['lat']
LONGITUD = config['target_city']['lon']
CIUDAD = config['target_city']['name']

FECHA_INICIO = config['data_sources']['climate']['start_date']
FECHA_FIN = config['data_sources']['climate']['end_date']

# Si la fecha es 'today', usamos la fecha real de hoy
if FECHA_FIN == 'today':
    FECHA_FIN = date.today().strftime("%Y-%m-%d")

RAW_DATA_PATH = config['paths']['raw_data']
OUTPUT_FILENAME = os.path.join(RAW_DATA_PATH, f'clima_{CIUDAD.lower()}_openmeteo.csv')

def fetch_climate_data():
    print(f"Iniciando descarga para {CIUDAD} (Lat: {LATITUD}, Lon: {LONGITUD})...")
    
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": LATITUD,
        "longitude": LONGITUD,
        "start_date": FECHA_INICIO,
        "end_date": FECHA_FIN,
        "daily": ["temperature_2m_mean", "precipitation_sum"],
        "timezone": "auto"
    }
    
    try:
        # Hacemos la llamada a la API
        response = requests.get(url, params=params, timeout=60) # 60 seg de paciencia
        response.raise_for_status() # Lanza un error si la API falla
        
        data = response.json()
        
        print("¡Datos recibidos! Procesando y guardando...")
        
        # Convertimos la respuesta JSON a un DataFrame de Pandas
        daily_data = data['daily']
        df = pd.DataFrame()
        df['fecha'] = pd.to_datetime(daily_data['time'])
        df['temp_media_c'] = daily_data['temperature_2m_mean']
        df['precip_total_mm'] = daily_data['precipitation_sum']
        
        # Guardamos el archivo
        os.makedirs(RAW_DATA_PATH, exist_ok=True)
        df.to_csv(OUTPUT_FILENAME, index=False)
        
        print(f"\n--- ¡ÉXITO TOTAL! ---")
        print(f"Se guardaron {len(df)} filas de datos climáticos en:")
        print(OUTPUT_FILENAME)
        print("\n--- Muestra de los datos ---")
        print(df.head())

    except requests.exceptions.RequestException as e:
        print(f"\n--- ERROR ---")
        print(f"No se pudo conectar a la API de Open-Meteo: {e}")
        print("Por favor, revisa tu conexión a internet.")

def main():
    print("Iniciando pipeline de extracción de datos climáticos (v14.0 - Open-Meteo)...")
    fetch_climate_data()
    print("Pipeline de extracción finalizado. Por fin.")

if __name__ == "__main__":
    main()