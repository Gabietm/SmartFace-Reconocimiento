import cv2
import sqlite3
import numpy as np
import ast
import supervision as sv
import threading
from ultralytics import YOLO
from deepface import DeepFace
from scipy.spatial.distance import cosine

model = YOLO('yolov8n.pt') 
tracker = sv.ByteTrack()
box_annotator = sv.BoxAnnotator()
label_annotator = sv.LabelAnnotator()

# Variables globales para el hilo de reconocimiento
reconocimiento_activo = {}
resultados_reconocimiento = {}

def cargar_usuarios():
    conexion = sqlite3.connect('base_de_datos/control_acceso.db')
    cursor = conexion.cursor()
    cursor.execute("SELECT nombres, apellidos, firma_facial FROM usuarios")
    data = cursor.fetchall()
    conexion.close()
    return [{"nombre": f"{n[0]} {n[1]}", "firma": np.array(ast.literal_eval(n[2]))} for n in data]

usuarios = cargar_usuarios()

def tarea_reconocimiento(tracker_id, recorte):
    """Esta tarea corre en segundo plano para no congelar el video"""
    try:
        # Usamos VGG-Face: Mucho más resistente a ángulos y distancia
        emb = DeepFace.represent(recorte, model_name="VGG-Face", detector_backend='retinaface', enforce_detection=True)[0]["embedding"]
        
        distancia_min = 1.0
        nombre_detectado = "Desconocido"
        
        for u in usuarios:
            distancia = cosine(emb, u["firma"])
            if distancia < distancia_min:
                distancia_min = distancia
                if distancia < 0.6: # Umbral más permisivo
                    nombre_detectado = u["nombre"]
        
        resultados_reconocimiento[tracker_id] = nombre_detectado
    except:
        resultados_reconocimiento[tracker_id] = "Desconocido"
    reconocimiento_activo[tracker_id] = False

def reconocer():
    cap = cv2.VideoCapture(0)
    cache_nombres = {}

    while True:
        ret, frame = cap.read()
        if not ret: break

        results = model(frame, verbose=False)[0]
        detections = sv.Detections.from_ultralytics(results)
        detections = tracker.update_with_detections(detections)

        labels = []
        for i, tracker_id in enumerate(detections.tracker_id):
            nombre = resultados_reconocimiento.get(tracker_id, "Detectando...")
            
            if tracker_id not in reconocimiento_activo or not reconocimiento_activo[tracker_id]:
                # Lanzar reconocimiento en hilo separado (esto elimina los cortes)
                x1, y1, x2, y2 = detections.xyxy[i].astype(int)
                recorte = frame[y1:y2, x1:x2] 
                
                if recorte.size > 0:
                    reconocimiento_activo[tracker_id] = True
                    threading.Thread(target=tarea_reconocimiento, args=(tracker_id, recorte), daemon=True).start()
            
            labels.append(nombre)

        frame = box_annotator.annotate(scene=frame, detections=detections)
        frame = label_annotator.annotate(scene=frame, detections=detections, labels=labels)
        cv2.imshow('SmartFace Pro', frame)
        if cv2.waitKey(1) == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    reconocer()