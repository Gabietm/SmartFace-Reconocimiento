import sqlite3
import os
import cv2
import numpy as np
from insightface.app import FaceAnalysis

# Inicializamos el motor de InsightFace
app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 480))

def procesar_y_guardar_usuario(cedula, nombres, apellidos, carrera, es_activo):
    ruta_foto = f"fotos_registros/{cedula}.jpg"
    
    if not os.path.exists(ruta_foto):
        return False, f"Error: No se encuentra la foto en {ruta_foto}."

    print("Procesando firma facial con ArcFace (InsightFace)...")
    try:
        # Cargar imagen y extraer embedding
        img = cv2.imread(ruta_foto)
        faces = app.get(img)
        
        if len(faces) == 0:
            return False, "Error: No se detectó ningún rostro en la foto."
        
        # Convertimos el array de numpy a lista para poder guardarlo como texto en SQL
        firma = str(faces[0].embedding.tolist())

        # Conectar a la base de datos
        conexion = sqlite3.connect('base_de_datos/control_acceso.db')
        cursor = conexion.cursor()
        
        # Insertamos o reemplazamos el usuario
        # es_activo se convierte a int: True -> 1, False -> 0
        cursor.execute('''
            INSERT OR REPLACE INTO usuarios (cedula, nombres, apellidos, carrera_especialidad, estado_financiero, firma_facial)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (cedula, nombres, apellidos, carrera, int(es_activo), firma))
        
        conexion.commit()
        conexion.close()
        
        estado_texto = "Activo" if es_activo else "Suspendido"
        return True, f"Registro exitoso: {nombres} {apellidos} guardado como {estado_texto}."
        
    except Exception as e:
        return False, f"Error en el proceso de registro: {str(e)}"

if __name__ == '__main__':
    print("--- Registro de Usuario SmartFace (Versión Booleana) ---")
    cedula = input("Cédula: ")
    nombres = input("Nombres: ")
    apellidos = input("Apellidos: ")
    carrera = input("Carrera: ")
    
    # Captura del estado booleano
    entrada = input("¿Está activo? (1 = Sí, 0 = No): ")
    es_activo = True if entrada == '1' else False
    
    exito, msg = procesar_y_guardar_usuario(cedula, nombres, apellidos, carrera, es_activo)
    print(msg)