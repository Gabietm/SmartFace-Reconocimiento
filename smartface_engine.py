"""
smartface_engine.py - Motor de reconocimiento facial optimizado para SmartFace Pro
"""

import multiprocessing as mp
import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
from config import UMBRAL_RECONOCIMIENTO, MODELO_YOLO, DB_PATH
from bd import UniversityDatabase

def worker_ia(cola_entrada, cola_salida, db_path):
    """Worker que procesa los rostros en paralelo utilizando una ruta de BD propia para evitar conflictos"""
    
    db = UniversityDatabase(db_path)
    
    from insightface.app import FaceAnalysis
    app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 480))
    
    usuarios = db.obtener_todos_estudiantes()
    print(f"🧠 Worker iniciado con {len(usuarios)} estudiantes cargados correctamente.")
    
    while True:
        mensaje = cola_entrada.get()
        if mensaje is None:
            break
            
        tracker_id, recorte = mensaje
        
        # Señal para recargar estudiantes desde la base de datos
        if tracker_id == "RELOAD":
            usuarios = db.obtener_todos_estudiantes()
            print(f"🔄 Worker recargó la base de datos. Total estudiantes: {len(usuarios)}")
            continue
            
        if tracker_id is None:
            break
            
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
                            firma_u = np.array(u["firma"])
                            norm_emb = np.linalg.norm(emb)
                            norm_firma = np.linalg.norm(firma_u)
                            
                            if norm_emb > 0 and norm_firma > 0:
                                distancia = 1 - np.dot(emb, firma_u) / (norm_emb * norm_firma)
                                
                                if distancia < distancia_min:
                                    distancia_min = distancia
                                    resultado = {
                                        "id": u["id"],
                                        "nombre": u["nombre"],
                                        "es_activo": u["es_activo"],
                                        "similitud": float(1 - distancia_min)
                                    }
            except Exception as e:
                print(f"Error procesando rostro en worker: {e}")
                
        cola_salida.put((tracker_id, resultado))

class SmartFaceEngine:
    """Motor de reconocimiento facial optimizado para control de acceso universitario"""
    
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.db = UniversityDatabase(db_path)
        
        # Inicializar YOLO para detección de personas
        self.model = YOLO(MODELO_YOLO)
        self.tracker = sv.ByteTrack()
        
        # Colas de comunicación segura para multiprocesamiento
        self.cola_entrada = mp.Queue()
        self.cola_salida = mp.Queue()
        
        # Lanzar el proceso worker pasando la ruta de la BD (evita errores de conexión compartida)
        self.worker = mp.Process(
            target=worker_ia, 
            args=(self.cola_entrada, self.cola_salida, self.db_path)
        )
        self.worker.start()
        
        self.resultados = {}
        self.en_proceso = set()
        print("🚀 Motor de reconocimiento facial optimizado iniciado exitosamente.")
    
    def procesar_frame(self, frame):
        """Procesa el fotograma aplicando filtros de región central y gestión asíncrona"""
        h, w, _ = frame.shape
        
        # Definir una Zona de Interés (ROI) central del 70% para filtrar falsos positivos
        margin_x = int(w * 0.15)
        margin_y = int(h * 0.15)
        roi_box = [margin_x, margin_y, w - margin_x, h - margin_y]
        
        # Detectar personas usando YOLOv8
        results = self.model(frame, verbose=False, classes=[0])[0]
        detections = sv.Detections.from_ultralytics(results)
        detections = self.tracker.update_with_detections(detections)
        
        # Vaciar la cola de resultados del worker de forma no bloqueante
        while not self.cola_salida.empty():
            try:
                t_id, resultado = self.cola_salida.get_nowait()
                self.resultados[t_id] = resultado
                self.en_proceso.discard(t_id)
                
                # Registrar log en base de datos si el estudiante fue reconocido con éxito
                if resultado.get("id") is not None:
                    self.db.registrar_log(
                        estudiante_id=resultado["id"],
                        similitud=resultado["similitud"],
                        reconocido=True
                    )
            except Exception:
                break
                
        if len(detections) > 0:
            for i, tracker_id in enumerate(detections.tracker_id):
                if tracker_id is None:
                    continue
                
                x1, y1, x2, y2 = detections.xyxy[i].astype(int)
                
                # Validar si la persona se encuentra dentro de la zona central de escaneo (ROI)
                centro_x = (x1 + x2) // 2
                centro_y = (y1 + y2) // 2
                en_roi = (roi_box[0] <= centro_x <= roi_box[2]) and (roi_box[1] <= centro_y <= roi_box[3])
                
                if not en_roi:
                    continue # Omitir detecciones fuera del área central de control
                
                if tracker_id in self.resultados:
                    resultado = self.resultados[tracker_id]
                    nombre = resultado["nombre"]
                elif tracker_id in self.en_proceso:
                    nombre = "Analizando..."
                else:
                    # Recortar región del rostro de manera segura dentro de los límites del frame
                    rx1, ry1 = max(0, x1), max(0, y1)
                    rx2, ry2 = min(w, x2), min(h, y2)
                    recorte = frame[ry1:ry2, rx1:rx2].copy()
                    
                    if recorte.size > 0:
                        self.en_proceso.add(tracker_id)
                        self.cola_entrada.put((tracker_id, recorte))
                    nombre = "Analizando..."
                    
        return frame
    
    def obtener_ultimo_estudiante(self):
        """Retorna el último registro de estudiante identificado con éxito"""
        if self.resultados:
            for tracker_id in reversed(list(self.resultados.keys())):
                resultado = self.resultados[tracker_id]
                if resultado.get("id") is not None:
                    return resultado
        return None
    
    def recargar_datos(self):
        """Envía una señal al proceso worker para actualizar los rostros y estados desde la BD"""
        try:
            self.cola_entrada.put(("RELOAD", None))
        except Exception as e:
            print(f"Error al enviar orden de recarga al worker: {e}")
            
    def reiniciar_sesion(self):
        """Limpia los resultados anteriores para permitir un nuevo escaneo limpio"""
        self.resultados.clear()
        self.en_proceso.clear()
        self.recargar_datos()
    
    def cerrar(self):
        """Finaliza ordenadamente el proceso worker de IA y libera recursos"""
        try:
            self.cola_entrada.put((None, None))
            self.worker.join(timeout=2)
            if self.worker.is_alive():
                self.worker.terminate()
        except Exception:
            pass
        print("🛑 Motor de reconocimiento facial cerrado correctamente.")