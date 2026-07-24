"""
_registrar_usuario_.py - Registro de estudiantes e inserción de firma facial en SmartFace
"""

import os
import cv2
import numpy as np
from insightface.app import FaceAnalysis
from bd import UniversityDatabase  # Módulo de base de datos correcto

# Variable global para el modelo (inicialmente vacía)
_face_app = None

def get_face_app():
    """Función de carga diferida (Lazy Loading) para evitar congelamientos al iniciar"""
    global _face_app
    if _face_app is None:
        print("Cargando modelos de InsightFace en memoria (esto puede tardar unos segundos)...")
        _face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        _face_app.prepare(ctx_id=0, det_size=(640, 480))
    return _face_app

def procesar_y_guardar_usuario(cedula: str, nombre: str, apellido: str, email: str, carrera: str, semestre: int = 1):
    ruta_foto = f"fotos_registros/{cedula}.jpg"
    
    if not os.path.exists(ruta_foto):
        return False, f"Error: No se encuentra la foto en {ruta_foto}."

    print("Procesando firma facial con ArcFace (InsightFace)...")
    try:
        app = get_face_app()

        img = cv2.imread(ruta_foto)
        faces = app.get(img)
        
        if len(faces) == 0:
            return False, "Error: No se detectó ningún rostro en la foto."
        
        embedding = faces[0].embedding

        db = UniversityDatabase()
        
        estudiante_id = db.registrar_estudiante(
            cedula=cedula,
            nombre=nombre,
            apellido=apellido,
            email=email,
            carrera=carrera,
            semestre=semestre,
            firma_facial=embedding
        )
        
        return True, f"¡Registro exitoso! {nombre} {apellido} guardado con ID #{estudiante_id}."
        
    except Exception as e:
        return False, f"Error en el proceso de registro: {str(e)}"