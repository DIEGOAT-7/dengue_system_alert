import pandas as pd
import numpy as np
import xgboost as xgb
import os
from datetime import timedelta

# CARGAR DATOS
PROCESSED_DATA_PATH = os.path.join('data', '03_processed')
MASTER_FILE = os.path.join(PROCESSED_DATA_PATH, 'master_dataset_cali.parquet')
EXPORT_PATH = os.path.join('data', '04_output')
os.makedirs(EXPORT_PATH, exist_ok=True)
OUTPUT_FILE = os.path.join(EXPORT_PATH, 'tablero_dengue_final.csv')

print("Cargando dataset maestro...")
df = pd.read_parquet(MASTER_FILE)

# INGENIERÍA DE CARACTERÍSTICAS (Función Reutilizable)
# Esta función debe ser IDÉNTICA a la del notebook para que el modelo entienda
def engineer_features(df_input):
    df_eng = df_input.copy()
    
    # Lags de Inercia (Casos)
    for lag in range(1, 5):
        df_eng[f'casos_lag_{lag}'] = df_eng['casos_dengue'].shift(lag)
    
    # Lags de Clima
    for lag in range(1, 5):
        df_eng[f'temp_lag_{lag}'] = df_eng['temp_media_semanal'].shift(lag)
        df_eng[f'precip_lag_{lag}'] = df_eng['precip_total_semanal'].shift(lag)
        
    # Ventanas Móviles
    df_eng['temp_promedio_4sem'] = df_eng['temp_media_semanal'].shift(1).rolling(window=4).mean()
    df_eng['precip_total_4sem'] = df_eng['precip_total_semanal'].shift(1).rolling(window=4).sum()
    
    # Estacionalidad
    df_eng['semana_del_año'] = df_eng.index.isocalendar().week.astype(int)
    df_eng['mes_del_año'] = df_eng.index.month.astype(int)
    
    return df_eng

# Aplicamos ingeniería al histórico completo
df_model = engineer_features(df)
df_model = df_model.dropna() # Limpiamos los NaNs iniciales del histórico

# RE-ENTRENAMIENTO DEL MODELO
# Entrenamos con TODOS los datos disponibles hasta hoy (sin dividir train/test)
# para que el modelo tenga la máxima "memoria" reciente.
print("Re-entrenando modelo con todo el histórico...")

features = [col for col in df_model.columns if col not in ['casos_dengue', 'tasa_incidencia_100k', 'poblacion']]
target = 'casos_dengue'

X = df_model[features]
y = df_model[target]

model = xgb.XGBRegressor(
    n_estimators=1000,
    learning_rate=0.05,
    early_stopping_rounds=50,
    random_state=42
)
# Usamos el mismo X, y como eval_set para que early_stopping funcione
model.fit(X, y, eval_set=[(X, y)], verbose=False)

# PREDICCIÓN RECURSIVA (El Futuro)
print("Generando predicciones para las próximas 4 semanas...")

# Tomamos la última fila real como punto de partida
last_date = df.index[-1]
future_dates = [last_date + timedelta(weeks=i) for i in range(1, 5)]

# Creamos un DataFrame temporal que irá creciendo
df_future = df.copy()

for date in future_dates:
    # 1. Añadimos una nueva fila vacía para la fecha futura
    # (Necesitamos rellenar el clima futuro... asumiremos el promedio histórico o el último dato)
    # Para simplificar este MVP, usaremos el clima de la última semana conocida (Persistencia)
    last_row = df_future.iloc[-1]
    new_row = pd.DataFrame(index=[date])
    new_row['temp_media_semanal'] = last_row['temp_media_semanal']
    new_row['precip_total_semanal'] = last_row['precip_total_semanal']
    new_row['poblacion'] = last_row['poblacion']
    new_row['casos_dengue'] = np.nan # Esto es lo que vamos a predecir
    
    # Usamos pd.concat en lugar de append (deprecado)
    df_future = pd.concat([df_future, new_row])
    
    # 2. Recalculamos TODAS las features (lags, rolling, etc.)
    # Esto llena los huecos de 'casos_lag_1' usando la predicción de la vuelta anterior
    df_future_eng = engineer_features(df_future)
    
    # 3. Predecimos SOLO la fila actual (la última)
    row_to_predict = df_future_eng.iloc[[-1]][features]
    prediction = model.predict(row_to_predict)[0]
    
    # 4. ¡Guardamos la predicción como si fuera un dato real!
    # (Para que la siguiente vuelta del bucle pueda usarla como lag)
    # Usamos .iloc para asignar al último índice
    df_future.iloc[-1, df_future.columns.get_loc('casos_dengue')] = max(0, int(prediction)) # Evitamos negativos

print(f"Predicciones generadas: {df_future['casos_dengue'].tail(4).values}")

# EXPORTAR PARA TABLEAU
print("Preparando archivo final para Tableau...")

# Etiquetamos los datos: 'Histórico' vs 'Pronóstico'
df_export = df_future.copy()
df_export['Tipo de Dato'] = 'Histórico'
# Las últimas 4 filas son Pronóstico
df_export.iloc[-4:, df_export.columns.get_loc('Tipo de Dato')] = 'Pronóstico'

# Seleccionamos columnas clave para el Dashboard
cols_export = ['casos_dengue', 'Tipo de Dato', 'temp_media_semanal', 'precip_total_semanal']
df_export = df_export[cols_export].reset_index().rename(columns={'index': 'Fecha'})

# Guardamos
df_export.to_csv(OUTPUT_FILE, index=False)
print(f"¡ÉXITO! Archivo exportado en: {OUTPUT_FILE}")