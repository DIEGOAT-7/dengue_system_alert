import pandas as pd
import os
import yaml
from sodapy import Socrata

# CARGAR CONFIGURACIÓN
print("Cargando configuración desde config.yaml...")
try:
    with open("config.yaml", "r") as file:
        config = yaml.safe_load(file)
except FileNotFoundError:
    raise FileNotFoundError("¡ERROR! No se encontró el archivo 'config.yaml' en la raíz del proyecto.")

# ASIGNAR VARIABLES DESDE EL CONFIG
# Variables de la Ciudad y Datos
TARGET_MUNICIO = config['target_city']['name'] # Ej: "CALI"
DATASET_ID = config['data_sources']['sivigila']['dataset_id'] # Ej: "4hyg-wa9d"
EVENT_NAME = config['data_sources']['sivigila']['event_name'] # Ej: "DENGUE"

# Rutas
RAW_DATA_PATH = config['paths']['raw_data']
OUTPUT_FILENAME = f"sivigila_historico_{TARGET_MUNICIO.lower()}.csv"
OUTPUT_FILE = os.path.join(RAW_DATA_PATH, OUTPUT_FILENAME)

# Columnas del Esquema (Estas suelen ser fijas en el dataset del INS, las dejamos aquí)
COL_MUNICIPIO = 'municipio_ocurrencia'
COL_DEPARTAMENTO = 'departamento_ocurrencia'
COL_EVENTO = 'nombre_evento'
COL_ANO = 'ano'
COL_SEMANA = 'semana'
COL_CASOS = 'conteo'

def fetch_sivigila_data():
    """
    Descarga datos históricos de SIVIGILA basados en el archivo de configuración.
    """
    print(f"--- Iniciando descarga SIVIGILA para: {TARGET_MUNICIO} ---")
    print(f"Dataset ID: {DATASET_ID}")
    print("Conectando a Socrata (datos.gov.co)...")
    
    try:
        client = Socrata("www.datos.gov.co", None, timeout=120)

        # Consulta SoQL Parametrizada
        # Nota: Usamos '>= 2015' como base segura para histórico
        soql_query = f"""
        SELECT
            {COL_ANO} AS ano,
            {COL_SEMANA} AS semana,
            {COL_CASOS} AS casos_dengue
        WHERE
            upper({COL_EVENTO}) = '{EVENT_NAME.upper()}'
            AND upper({COL_MUNICIPIO}) = '{TARGET_MUNICIO.upper()}'
            AND {COL_ANO} >= 2015
        LIMIT 50000
        """
        
        print(f"Ejecutando consulta para {EVENT_NAME} en {TARGET_MUNICIO}...")
        results = client.get(DATASET_ID, query=soql_query)
        
        if not results:
            print(f"ADVERTENCIA: La consulta no devolvió resultados para {TARGET_MUNICIO}.")
            print("Verifica que el nombre del municipio en config.yaml sea correcto (ej. 'BOGOTA D.C.' vs 'BOGOTA').")
            return

        df_sivigila_historico = pd.DataFrame.from_records(results)
        
        print(f"\n[ÉXITO] ¡Descarga completada!")
        print(f"Registros encontrados: {len(df_sivigila_historico)}")
        print(f"Rango de años: {sorted(df_sivigila_historico['ano'].unique(), reverse=True)}")

        # Guardar
        os.makedirs(RAW_DATA_PATH, exist_ok=True)
        df_sivigila_historico.to_csv(OUTPUT_FILE, index=False)
        print(f"Archivo guardado en: {OUTPUT_FILE}")

    except Exception as e:
        print(f"\n--- ¡ERROR CRÍTICO! ---")
        print(f"Fallo en el pipeline de SIVIGILA: {e}")

def main():
    fetch_sivigila_data()

if __name__ == "__main__":
    main()