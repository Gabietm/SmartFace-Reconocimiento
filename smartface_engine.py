"""
face_engine.py - Motor de reconocimiento facial (adaptado para universidad)
"""

import multiprocessing as mp
import cv2
import numpy as np
import json
from ultralytics import YOLO
import supervision as sv
from insightface.app import FaceAnalysis
from config import UMBRAL_RECONOCIMIENTO, MODELO_YOLO
from bd import UniversityDatabase

def worker_ia(cola_entrada, cola_salida, db):
    """Worker que procesa los rostros en paralelo"""
    
    # Inicializar InsightFace
    app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 480))
    
    # Obtener estudiantes de la base de datos
    usuarios = db.obtener_todos_estudiantes()
    
    print(f"🧠 Worker iniciado con {len(usuarios)} estudiantes cargados")
    
    while True:
        tracker_id, recorte = cola_entrada.get()
        if tracker_id is None:
            break
        
        # Inicializar resultado por defecto
        resultado = {
            "id": None,
            "nombre": "Desconocido",
            "es_activo": False,
            "similitud": 0.0
        }
        
        if recorte is not None and recorte.size > 0:
            try:
                faces = app.get(recorte)
                
                if len(faces) > 0:
                    emb = faces[0].embedding
                    distancia_min = UMBRAL_RECONOCIMIENTO
                    
                    for u in usuarios:
                        if u["firma"] is not None:
                            # Calcular distancia coseno
                            distancia = 1 - np.dot(emb, u["firma"]) / (
                                np.linalg.norm(emb) * np.linalg.norm(u["firma"]) + 1e-8
                            )
                            
                            if distancia < distancia_min:
                                distancia_min = distancia
                                resultado = {
                                    "id": u["id"],
                                    "nombre": u["nombre"],
                                    "es_activo": u["es_activo"],
                                    "similitud": 1 - distancia_min
                                }
            except Exception as e:
                print(f"Error procesando rostro: {e}")
        
        cola_salida.put((tracker_id, resultado))

class SmartFaceEngine:
    """Motor de reconocimiento facial para la universidad"""
    
    def __init__(self, db_path=None):
        self.db = UniversityDatabase(db_path) if db_path else UniversityDatabase()
        
        # Inicializar YOLO para detección de personas
        self.model = YOLO(MODELO_YOLO)
        self.tracker = sv.ByteTrack()
        
        # Anotadores
        self.box_annotator = sv.BoxAnnotator()
        self.label_annotator = sv.LabelAnnotator()
        
        # Colas para comunicación con el worker
        self.cola_entrada = mp.Queue()
        self.cola_salida = mp.Queue()
        
        # Iniciar worker en proceso separado
        self.worker = mp.Process(
            target=worker_ia, 
            args=(self.cola_entrada, self.cola_salida, self.db)
        )
        self.worker.start()
        
        # Cache de resultados
        self.resultados = {}
        self.en_proceso = set()
        
        print("🚀 Motor de reconocimiento facial iniciado")
    
    def procesar_frame(self, frame):
        """Procesa un frame de video y devuelve el frame anotado"""
        
        # Detectar personas
        results = self.model(frame, verbose=False, classes=[0])[0]
        detections = sv.Detections.from_ultralytics(results)
        detections = self.tracker.update_with_detections(detections)
        
        # Recibir resultados del worker
        while not self.cola_salida.empty():
            t_id, resultado = self.cola_salida.get()
            self.resultados[t_id] = resultado
            self.en_proceso.discard(t_id)
        
        # Procesar cada detección
        if len(detections) > 0:
            for i, tracker_id in enumerate(detections.tracker_id):
                if tracker_id is None:
                    continue
                
                # Obtener o asignar resultado
                if tracker_id in self.resultados:
                    resultado = self.resultados[tracker_id]
                    nombre = resultado["nombre"]
                    es_activo = resultado["es_activo"]
                    color = sv.Color(r=0, g=255, b=0) if es_activo else sv.Color(r=255, g=0, b=0)
                    
                    # Registrar log si es reconocido
                    if resultado["id"] is not None:
                        self.db.registrar_log(
                            estudiante_id=resultado["id"],
                            similitud=resultado["similitud"],
                            reconocido=True
                        )
                
                elif tracker_id in self.en_proceso:
                    color = sv.Color(r=128, g=128, b=255)
                    nombre = "Analizando..."
                
                else:
                    # Enviar a procesar
                    x1, y1, x2, y2 = detections.xyxy[i].astype(int)
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
                    
                    recorte = frame[y1:y2, x1:x2].copy()
                    
                    if recorte.size > 0:
                        self.en_proceso.add(tracker_id)
                        self.cola_entrada.put((tracker_id, recorte))
                    
                    color = sv.Color(r=128, g=128, b=255)
                    nombre = "Analizando..."
                
                # Anotar en el frame
                single_det = detections[i:i+1]
                frame = self.box_annotator.annotate(
                    scene=frame, 
                    detections=single_det,
                    color=color
                )
                frame = self.label_annotator.annotate(
                    scene=frame, 
                    detections=single_det,
                    labels=[nombre],
                    color=color
                )
        
        return frame
    
    def obtener_ultimo_estudiante(self):
        """Obtiene el último estudiante reconocido"""
        if self.resultados:
            # Obtener el resultado más reciente con ID
            for tracker_id in reversed(list(self.resultados.keys())):
                resultado = self.resultados[tracker_id]
                if resultado["id"] is not None:
                    return resultado
        return None
    
    def cerrar(self):
        """Cierra el motor y el worker"""
        self.cola_entrada.put((None, None))
        self.worker.join(timeout=2)
        if self.worker.is_alive():
            self.worker.terminate()
        print("🛑 Motor de reconocimiento facial cerrado")