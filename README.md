# SmartFace Pro: Sistema de Control de Acceso con IA

SmartFace Pro es un sistema avanzado de control de acceso que utiliza reconocimiento facial mediante redes neuronales (ArcFace) y detección de personas en tiempo real (YOLOv8), con una lógica de semaforización basada en el estado financiero del usuario registrado.

## Características Principales

* **Reconocimiento Facial de Alta Precisión:** Basado en el motor InsightFace.

* **Detección y Seguimiento:** Implementa YOLOv8 con optimización de rendimiento para mantener la identidad en el flujo de video.

* **Pre-carga Inteligente en Segundo Plano:** Inicialización simultánea de la cámara web y el motor de IA al arrancar la aplicación, garantizando que el sistema esté completamente listo para escanear de forma instantánea al hacer clic.

* **Sincronización Financiera y Tasa BCV:** Consulta automática de la tasa oficial del Banco Central de Venezuela para calcular y mostrar deudas pendientes en euros (€) y su equivalencia exacta en bolívares (Bs.).

* **Semaforización Visual:**

  *🟢 **Verde:** Acceso autorizado (Usuario Solvente / Activo).
  *🔴 **Rojo:** Acceso restringido (Usuario Moroso / Inactivo).

* **Arquitectura Multiproceso y Fluida:** Procesamiento asíncrono con frame skipping para asegurar una visualización de video sin interrupciones ni latencia.

* **Interfaz Neumórfica Moderna:** Desarrollada con Flet y una paleta de colores Adobe Color optimizada.

## Estructura del Sistema 

El sistema se auto-configura al iniciarse, creando las carpetas, directorios de registros fotográficos y bases de datos necesarias para su funcionamiento.  

## RequisitosPython 

* 3.10 o superior.
* Librerías requeridas (instalar vía pip):
```Bash
pip install -r requirements.txt