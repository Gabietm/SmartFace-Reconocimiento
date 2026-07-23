"""
registro_usuario.py - Registro de estudiantes e inserción de firma facial en SmartFace
"""

import os
import cv2
import numpy as np
from insightface.app import FaceAnalysis
from bd import UniversityDatabase  # Conexión directa con tu gestor de BD

# Inicializamos el motor de InsightFace
app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 480))

def procesar_y_guardar_usuario(cedula: str, nombre: str, apellido: str, email: str, carrera: str, semestre: int = 1):
    ruta_foto = f"fotos_registros/{cedula}.jpg"
    
    if not os.path.exists(ruta_foto):
        return False, f"Error: No se encuentra la foto en {ruta_foto}."

    print("Procesando firma facial con ArcFace (InsightFace)...")
    try:
        # 1. Cargar imagen y extraer embedding
        img = cv2.imread(ruta_foto)
        faces = app.get(img)
        
        if len(faces) == 0:
            return False, "Error: No se detectó ningún rostro en la foto."
        
        # Pasamos directamente el array de numpy (InsightFace nos da ndarray)
        embedding = faces[0].embedding

        # 2. Conectar a la base de datos mediante bd.py
        db = UniversityDatabase()
        
        # 3. Registrar estudiante
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

if __name__ == '__main__':
    print("--- Registro de Estudiante SmartFace Pro ---")
    cedula = input("Cédula: ")
    nombre = input("Nombre: ")
    apellido = input("Apellido: ")
    email = input("Email: ")
    carrera = input("Carrera: ")
    
    sem_in = input("Semestre (por defecto 1): ")
    semestre = int(sem_in) if sem_in.isdigit() else 1
    
    exito, msg = procesar_y_guardar_usuario(
        cedula=cedula, 
        nombre=nombre, 
        apellido=apellido, 
        email=email, 
        carrera=carrera, 
        semestre=semestre
    )
    
    print("\n" + msg)