import multiprocessing as mp
import cv2
from ultralytics import YOLO
import supervision as sv
from insightface.app import FaceAnalysis
import numpy as np
import sqlite3
import ast

def worker_ia(cola_entrada, cola_salida, db_path):
    app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 480))
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT nombres, apellidos, firma_facial, estado_financiero FROM usuarios")
    data = cursor.fetchall()
    conn.close()
    
    usuarios = [{
        "nombre": f"{n[0]} {n[1]}", 
        "firma": np.array(ast.literal_eval(n[2])),
        "es_activo": bool(n[3]) 
    } for n in data]

    while True:
        tracker_id, recorte = cola_entrada.get()
        if tracker_id is None: break 
        
        faces = app.get(recorte)
        resultado = ("Desconocido", True)
        
        if len(faces) > 0:
            emb = faces[0].embedding
            distancia_min = 0.5
            for u in usuarios:
                distancia = 1 - np.dot(emb, u["firma"]) / (np.linalg.norm(emb) * np.linalg.norm(u["firma"]))
                if distancia < distancia_min:
                    distancia_min = distancia
                    resultado = (u["nombre"], u["es_activo"])
        
        cola_salida.put((tracker_id, resultado))

class SmartFaceEngine:
    def __init__(self, db_path='base_de_datos/control_acceso.db'):
        self.model = YOLO('yolov8n.pt')
        self.tracker = sv.ByteTrack()
        # Inicializamos anotadores básicos
        self.box_annotator = sv.BoxAnnotator()
        self.label_annotator = sv.LabelAnnotator()
        
        self.cola_entrada = mp.Queue()
        self.cola_salida = mp.Queue()
        
        self.worker = mp.Process(target=worker_ia, args=(self.cola_entrada, self.cola_salida, db_path))
        self.worker.start()
        
        self.resultados = {}
        self.en_proceso = set()

    def procesar_frame(self, frame):
        results = self.model(frame, verbose=False, classes=[0])[0]
        detections = sv.Detections.from_ultralytics(results)
        detections = self.tracker.update_with_detections(detections)
        
        while not self.cola_salida.empty():
            t_id, (nombre, es_activo) = self.cola_salida.get()
            self.resultados[t_id] = (nombre, es_activo)
            self.en_proceso.remove(t_id)
        
        # Procesamos cada detección individualmente para asegurar el color correcto
        for i, tracker_id in enumerate(detections.tracker_id):
            if tracker_id in self.resultados:
                nombre, es_activo = self.resultados[tracker_id]
                color = sv.Color(r=0, g=255, b=0) if es_activo else sv.Color(r=255, g=0, b=0)
                label = nombre
            elif tracker_id in self.en_proceso:
                color = sv.Color(r=128, g=0, b=128)
                label = "Analizando..."
            else:
                x1, y1, x2, y2 = detections.xyxy[i].astype(int)
                recorte = frame[max(0, y1):y2, max(0, x1):x2].copy()
                self.en_proceso.add(tracker_id)
                self.cola_entrada.put((tracker_id, recorte))
                color = sv.Color(r=128, g=0, b=128)
                label = "Analizando..."
            
            # Dibujamos cada detección una por una con su color específico
            single_det = detections[i:i+1]
            box_ann = sv.BoxAnnotator(color=color)
            lab_ann = sv.LabelAnnotator(color=color)
            
            frame = box_ann.annotate(scene=frame, detections=single_det)
            frame = lab_ann.annotate(scene=frame, detections=single_det, labels=[label])
            
        return frame
    
    def cerrar(self):
        self.cola_entrada.put((None, None))
        self.worker.join()