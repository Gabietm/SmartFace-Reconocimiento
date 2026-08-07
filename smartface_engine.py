import cv2
import numpy as np
import os
import sqlite3
import pickle

try:
    from insightface.app import FaceAnalysis
except ImportError:
    FaceAnalysis = None

class SmartFaceEngine:
    def __init__(self, db_path="base_de_datos"):
        self.db_path = db_path
        
        self._ultimo_estudiante = {
            "nombre": "Esperando escaneo...",
            "cedula": "",
            "solvencia": "0%",
            "morosidad": "0%"
        }
        
        if FaceAnalysis:
            self.app = FaceAnalysis(name="buffalo_l", providers=['CPUExecutionProvider'])
            self.app.prepare(ctx_id=0, det_size=(640, 640))
        else:
            self.app = None
            
        self.conocidos_embeddings = []
        self.conocidos_datos = []
        self.cargar_datos()

    def cargar_datos(self):
        """Carga los embeddings y datos imprimiendo el estado en consola"""
        self.conocidos_embeddings = []
        self.conocidos_datos = []
        
        # Cargar administrador si existe
        ruta_admin = os.path.join(self.db_path, "admin_embedding.pkl")
        if os.path.exists(ruta_admin):
            with open(ruta_admin, "rb") as f:
                admin_emb = pickle.load(f)
                self.conocidos_embeddings.append(admin_emb)
                self.conocidos_datos.append({
                    "nombre": "Administrador",
                    "cedula": "ADMIN",
                    "solvencia": "100%",
                    "morosidad": "0%"
                })
            print("[DEBUG] Administrador cargado correctamente.")

        # Buscar base de datos de estudiantes
        db_file = os.path.join(self.db_path, "database.db")
        if not os.path.exists(db_file) and os.path.exists("database.db"):
            db_file = "database.db"

        print(f"[DEBUG] Buscando base de datos en: {db_file}")

        if os.path.exists(db_file):
            try:
                conn = sqlite3.connect(db_file)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT cedula, nombres, apellidos FROM estudiantes")
                estudiantes = cursor.fetchall()
                conn.close()

                print(f"[DEBUG] Estudiantes encontrados en BD: {len(estudiantes)}")

                fotos_dir = "fotos"
                if not os.path.exists(fotos_dir):
                    print(f"[ADVERTENCIA] La carpeta '{fotos_dir}' no existe en el directorio de trabajo.")

                for est in estudiantes:
                    cedula = str(est['cedula']).strip()
                    nombre_completo = f"{est['nombres']} {est['apellidos']}"
                    
                    ruta_foto = None
                    for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG']:
                        candidato = os.path.join(fotos_dir, f"{cedula}{ext}")
                        if os.path.exists(candidato):
                            ruta_foto = candidato
                            break
                    
                    if ruta_foto and self.app:
                        img = cv2.imread(ruta_foto)
                        if img is not None:
                            faces = self.app.get(img)
                            if faces:
                                self.conocidos_embeddings.append(faces[0].embedding)
                                self.conocidos_datos.append({
                                    "nombre": nombre_completo,
                                    "cedula": cedula,
                                    "solvencia": "100%",
                                    "morosidad": "0%"
                                })
                                print(f"[ÉXITO] Embedding cargado para: {nombre_completo} (Cédula: {cedula})")
                            else:
                                print(f"[ERROR] No se detectó ningún rostro en la foto: {ruta_foto}")
                        else:
                            print(f"[ERROR] No se pudo leer la imagen: {ruta_foto}")
                    else:
                        print(f"[ERROR] No se encontró foto para la cédula '{cedula}' en la carpeta '{fotos_dir}'")
            except Exception as e:
                print(f"[ERROR] Excepción al conectar con la base de datos: {e}")
        else:
            print("[ADVERTENCIA] No se encontró archivo de base de datos SQLite.")

        print(f"[DEBUG] Total de rostros conocidos cargados en memoria: {len(self.conocidos_embeddings)}")

    def recargar_datos(self):
        self.cargar_datos()

    def obtener_ultimo_estudiante(self):
        return self._ultimo_estudiante

    def reiniciar_sesion(self):
        self._ultimo_estudiante = {
            "nombre": "Esperando escaneo...",
            "cedula": "",
            "solvencia": "0%",
            "morosidad": "0%"
        }

    def procesar_frame(self, frame):
        if self.app is None:
            return frame

        h, w, _ = frame.shape
        
        box_w, box_h = 300, 300
        x1 = (w - box_w) // 2
        y1 = (h - box_h) // 2
        x2 = x1 + box_w
        y2 = y1 + box_h

        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
        cv2.putText(
            frame, 
            "Coloque su rostro aqui", 
            (x1, max(y1 - 10, 20)), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            (255, 0, 0), 
            2
        )

        faces = self.app.get(frame)

        for face in faces:
            bbox = face.bbox.astype(int)
            emb = face.embedding
            fx1, fy1, fx2, fy2 = bbox[0], bbox[1], bbox[2], bbox[3]
            
            face_center_x = (fx1 + fx2) // 2
            face_center_y = (fy1 + fy2) // 2
            en_cuadro = (x1 <= face_center_x <= x2) and (y1 <= face_center_y <= y2)

            if en_cuadro:
                if len(self.conocidos_embeddings) > 0:
                    max_sim = 0.0
                    mejor_idx = -1
                    
                    for i, conocido_emb in enumerate(self.conocidos_embeddings):
                        sim = np.dot(emb, conocido_emb) / (np.linalg.norm(emb) * np.linalg.norm(conocido_emb))
                        if sim > max_sim:
                            max_sim = sim
                            mejor_idx = i

                    # Imprime en consola la similitud en tiempo real para calibración
                    print(f"[ESCANEO] Similitud máxima calculada: {max_sim:.4f}")

                    if max_sim >= 0.38 and mejor_idx != -1:
                        datos = self.conocidos_datos[mejor_idx]
                        self._ultimo_estudiante = {
                            "nombre": datos["nombre"],
                            "cedula": datos["cedula"],
                            "solvencia": datos["solvencia"],
                            "morosidad": "0%"
                        }
                        cv2.rectangle(frame, (fx1, fy1), (fx2, fy2), (0, 255, 0), 2)
                        cv2.putText(frame, f"{datos['nombre']} ({max_sim*100:.1f}%)", (fx1, max(fy1 - 10, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        break
                    else:
                        cv2.rectangle(frame, (fx1, fy1), (fx2, fy2), (0, 0, 255), 2)
                        cv2.putText(frame, f"Desconocido ({max_sim*100:.1f}%)", (fx1, max(fy1 - 10, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                else:
                    cv2.rectangle(frame, (fx1, fy1), (fx2, fy2), (0, 0, 255), 2)
                    cv2.putText(frame, "Sin base de datos / Sin foto", (fx1, max(fy1 - 10, 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            else:
                cv2.rectangle(frame, (fx1, fy1), (fx2, fy2), (0, 0, 255), 2)

        return frame

    def reconocer(self, frame):
        return self.procesar_frame(frame)

    def cerrar(self):
        pass