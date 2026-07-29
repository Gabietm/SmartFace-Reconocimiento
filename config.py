"""
config.py - Configuración central del sistema
"""

import sys
import os
from pathlib import Path

# Detectar si estamos ejecutando el script de Python o un .exe compilado
if getattr(sys, 'frozen', False):
    # Si es un ejecutable, tomamos la carpeta donde está el .exe
    BASE_DIR = Path(sys.executable).parent
else:
    # Si es desarrollo, tomamos la carpeta del archivo actual
    BASE_DIR = Path(__file__).parent
    
DB_PATH = BASE_DIR / "base_de_datos" / "control_acceso.db"
FOTOS_DIR = BASE_DIR / "fotos_registros"

# Configuración de reconocimiento
UMBRAL_RECONOCIMIENTO = 0.5  # Distancia mínima para considerar coincidencia
MODELO_YOLO = 'yolov8n.pt'   # Modelo de detección de personas

# Configuración de cámara
CAMARA_INDEX = 0  # 0 para cámara web por defecto
RESOLUCION_CAMARA = (640, 480)

# Configuración de UI
TEMA_COLOR = "#011C6B"
TEMA_COLOR_SECUNDARIO = "#00A8FF"

# Crear directorios necesarios
os.makedirs(BASE_DIR / "base_de_datos", exist_ok=True)
os.makedirs(BASE_DIR / "fotos_registros", exist_ok=True)