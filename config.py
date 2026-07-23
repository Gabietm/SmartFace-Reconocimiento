"""
config.py - Configuración central del sistema
"""

import os
from pathlib import Path

# Rutas
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "base_de_datos" / "control_acceso.db"

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
os.makedirs(BASE_DIR / "static" / "imagenes", exist_ok=True)