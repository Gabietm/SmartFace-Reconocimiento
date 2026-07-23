from smartface_engine import SmartFaceEngine
import cv2
import os

def inicializar_entorno():
    carpetas = ['base_de_datos', 'fotos_registros']
    for carpeta in carpetas:
        if not os.path.exists(carpeta):
            os.makedirs(carpeta)
            print(f"Directorio '{carpeta}' creado.")
            
if __name__ == '__main__':
    engine = SmartFaceEngine()
    cap = cv2.VideoCapture(0)
    contador = 0
    frame_final = None

    try:
        while True:
            ret, frame = cap.read()
            if not ret: break
            if frame_final is None: frame_final = frame
            
            if contador % 6 == 0:
                frame_final = engine.procesar_frame(frame)
            
            cv2.imshow('SmartFace Pro - Sistema Profesional', frame_final)
            contador += 1
            if cv2.waitKey(1) == ord('q'): break
    finally:
        engine.cerrar()
        cap.release()
        cv2.destroyAllWindows()