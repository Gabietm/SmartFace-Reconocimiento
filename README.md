# SmartFace Pro: Sistema de Control de Acceso con IA

SmartFace Pro es un sistema avanzado de control de acceso que utiliza reconocimiento facial mediante redes neuronales (ArcFace) y detección de personas en tiempo real (YOLOv8), con una lógica de semaforización basada en el estado financiero del usuario registrado.

## Características Principales
* **Reconocimiento Facial de Alta Precisión:** Basado en el motor InsightFace.
* **Detección y Seguimiento:** Implementa YOLOv8 con rastreo ByteTrack para mantener la identidad en el flujo de video.
* **Semaforización Visual:**
  * 🟢 **Verde:** Acceso autorizado (Usuario Activo).
  * 🔴 **Rojo:** Acceso restringido (Usuario Suspendido).
  * 🟣 **Morado:** Estado en análisis.
* **Arquitectura Multiproceso:** Procesamiento asíncrono para mantener el video fluido sin latencia.

## Estructura del Sistema
El sistema se auto-configura al iniciarse, creando las carpetas necesarias para su funcionamiento.

## Requisitos
* Python 3.10 o superior.
* Librerías requeridas (instalar vía pip):
```bash
pip install -r requirements.txt