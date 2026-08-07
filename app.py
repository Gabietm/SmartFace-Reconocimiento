"""
app.py - Aplicación para Flet (0.21.2+) con Integración OpenCV + SmartFaceEngine
Diseño Neumórfico con Paleta Adobe Color & Gradiente Moderno
"""

import flet as ft
import time
import threading
import cv2
import base64
import os
import datetime

from smartface_engine import SmartFaceEngine

# ============================================
# PALETA DE COLORES ADOBE COLOR
# ============================================

BG_COLOR = "#F2F2F2"       # Tono base neumórfico
TEXT_COLOR = "#2C3E50"     # Gris oscuro
ACCENT_BLUE = "#353FF2"    # Azul vibrante principal
ACCENT_MID = "#3084F2"     # Azul intermedio
ACCENT_LIGHT = "#2E97F2"   # Azul claro

# Gradiente moderno extraído de la paleta
GRADIENT_MODERNO = ft.LinearGradient(
    begin=ft.alignment.top_left,
    end=ft.alignment.bottom_right,
    colors=["#353FF2", "#3565F2", "#3084F2", "#2E97F2"]
)

def get_neumorphic_shadows():
    """Sombras optimizadas para la base #F2F2F2"""
    return [
        ft.BoxShadow(spread_radius=1, blur_radius=10, color="white", offset=ft.Offset(-5, -5)),
        ft.BoxShadow(spread_radius=1, blur_radius=10, color="#D0D5DD", offset=ft.Offset(5, 5))
    ]

def neu_container(content=None, padding=20, border_radius=20, expand=False, width=None, height=None, on_click=None, shape=None):
    return ft.Container(
        content=content, padding=padding,
        border_radius=border_radius if shape != ft.BoxShape.CIRCLE else None,
        shape=shape, bgcolor=BG_COLOR, width=width, height=height,
        expand=expand, on_click=on_click,
        shadow=get_neumorphic_shadows(),
        animate=ft.animation.Animation(300, ft.AnimationCurve.EASE_OUT)
    )

def crear_boton_gradiente(texto, icon=None, on_click=None, height=45, width=None, expand=False):
    """Generador modular de botones con gradiente uniforme"""
    controls_row = []
    if icon:
        controls_row.append(ft.Icon(icon, color="white", size=18))
    controls_row.append(ft.Text(texto, size=14, weight=ft.FontWeight.BOLD, color="white"))

    return ft.Container(
        alignment=ft.alignment.center,
        content=ft.Row(controls_row, alignment=ft.MainAxisAlignment.CENTER, spacing=8),
        gradient=GRADIENT_MODERNO,
        padding=ft.padding.symmetric(horizontal=25, vertical=10),
        border_radius=20,
        height=height,
        width=width,
        expand=expand,
        shadow=[ft.BoxShadow(spread_radius=1, blur_radius=8, color="#353FF2", offset=ft.Offset(0, 4))],
        on_click=on_click,
        animate=ft.animation.Animation(200, ft.AnimationCurve.EASE_IN_OUT)
    )

# ============================================
# CLASE PRINCIPAL DE LA APLICACIÓN
# ============================================

class UniversityApp(ft.Container):
    
    def __init__(self, page: ft.Page):
        super().__init__()
        self.page = page
        self.bgcolor = BG_COLOR
        self.expand = True
        self.padding = ft.padding.all(30)
        
        self.scanning = False
        self.engine = None
        self.cap = None  # Instancia de la cámara pre-cargada
        
        # Pre-cargar el motor de IA y la cámara en segundo plano al abrir la app
        threading.Thread(target=self._pre_cargar_motor, daemon=True).start()
        threading.Thread(target=self._pre_cargar_camara, daemon=True).start()
        
        # Píxel transparente en Base64 para inicializar la imagen
        self.transparent_pixel = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        )
        
        self.video_image = ft.Image(
            src_base64=self.transparent_pixel,
            width=640,
            height=480,
            fit=ft.ImageFit.CONTAIN,
            border_radius=15,
            visible=False
        )
        
        # Contenido dinámico de la barra lateral (Sidebar)
        self.sidebar_content = ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.START,
            spacing=15,
            controls=[
                ft.Icon(ft.icons.FACE_RETOUCHING_NATURAL, size=50, color=ACCENT_BLUE),
                ft.Text("SmartFace", size=20, weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
                ft.Container(height=20),
                ft.Icon(ft.icons.PERSON_SEARCH_OUTLINED, size=60, color=ACCENT_MID),
                ft.Text("Esperando escaneo...", size=16, weight=ft.FontWeight.W_500, color=TEXT_COLOR, text_align=ft.TextAlign.CENTER),
                ft.Text("Inicia el escaneo para ver los datos del estudiante.", size=12, color="#7F8C8D", text_align=ft.TextAlign.CENTER)
            ]
        )
        
        # Armar layout principal en la inicialización
        self.content = ft.Row(
            expand=True,
            spacing=30,
            controls=[
                self._build_sidebar(),
                self._build_main_area()
            ]
        )

    # --------------------------------------------
    # SIDEBAR
    # --------------------------------------------
    def _build_sidebar(self):
        return neu_container(
            width=280,
            padding=25,
            content=self.sidebar_content
        )
    
    def _update_sidebar_student(self, estudiante):
        """Actualiza la barra lateral con los datos del estudiante reconocido"""
        nombre = estudiante.get('nombre', 'Desconocido')
        cedula = estudiante.get('cedula', 'N/A')
        solvencia = estudiante.get('solvencia', '0%')
        morosidad = estudiante.get('morosidad', '0%')
        
        es_activo = nombre != "Desconocido" and nombre != "Esperando escaneo..."
        color_estado = ACCENT_BLUE if es_activo else "#FF1744"
        
        info_controls = [
            ft.Icon(ft.icons.VERIFIED_USER, size=50, color=color_estado),
            ft.Column([
                ft.Text("Estudiante / Usuario", size=11, color="#7F8C8D", weight=ft.FontWeight.BOLD),
                ft.Text(nombre, size=16, weight=ft.FontWeight.BOLD, color=TEXT_COLOR, text_align=ft.TextAlign.CENTER)
            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([
                ft.Icon(ft.icons.BADGE_OUTLINED, size=16, color=ACCENT_MID),
                ft.Text(f"Cédula: {cedula}", size=13, color=TEXT_COLOR)
            ], spacing=8),
            ft.Row([
                ft.Icon(ft.icons.PERCENT, size=16, color=ACCENT_MID),
                ft.Text(f"Solvencia: {solvencia}", size=13, color=TEXT_COLOR)
            ], spacing=8),
            ft.Row([
                ft.Icon(ft.icons.WARNING_OUTLINED, size=16, color="#FF1744"),
                ft.Text(f"Morosidad: {morosidad}", size=13, color=TEXT_COLOR)
            ], spacing=8),
            ft.Divider(height=1, color="#D0D5DD"),
            ft.Container(
                margin=ft.margin.only(top=10),
                content=ft.Row([
                    ft.Icon(ft.icons.CHECK_CIRCLE if es_activo else ft.icons.INFO, size=20, color=color_estado),
                    ft.Text("Verificado por SmartFace", size=11, color="#7F8C8D", italic=True)
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=5)
            )
        ]

        self.sidebar_content.controls = info_controls
        self.update()

    # --------------------------------------------
    # ÁREA PRINCIPAL
    # --------------------------------------------
    def _build_main_area(self):
        self.stats_section = self._build_stats_section()
        
        btn_cerrar = ft.IconButton(
            icon=ft.icons.CLOSE,
            icon_color=TEXT_COLOR,
            tooltip="Cerrar aplicación",
            on_click=lambda e: self._cerrar_app()
        )
        
        header_row = ft.Row(
            alignment=ft.MainAxisAlignment.END,
            controls=[btn_cerrar]
        )

        main_column = ft.Column(
            expand=True,
            spacing=15,
            controls=[
                header_row,
                self._build_camera_section(),
                self.stats_section
            ]
        )
        return main_column
        
    def _cerrar_app(self):
        self.scanning = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.page.window_destroy()
        
    def _build_stats_section(self):
        return ft.Row(
            height=180,
            spacing=30,
            controls=[
                neu_container(
                    expand=True,
                    content=ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=5,
                        controls=[
                            ft.Text("Estado del Sistema", size=16, color=TEXT_COLOR),
                            ft.Text("Activo", size=32, weight=ft.FontWeight.BOLD, color=ACCENT_BLUE),
                            ft.Text("Motor InsightFace listo", size=12, color="#7F8C8D")
                        ]
                    )
                )
            ]
        )
    
    def _build_camera_section(self):
        btn_escanear = crear_boton_gradiente("Escanear", on_click=self._start_scan, height=40, width=200)

        self.camera_content = ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            controls=[
                self.video_image,
                ft.Icon(ft.icons.VIDEOCAM_OUTLINED, size=80, color=ACCENT_MID),
                ft.Text("Cámara (Inactiva)", size=18, weight=ft.FontWeight.W_500, color=TEXT_COLOR),
                btn_escanear
            ]
        )

        return neu_container(
            expand=True,
            content=ft.Container(
                alignment=ft.alignment.center,
                content=self.camera_content
            )
        )

    def _pre_cargar_motor(self):
        """Inicializa el motor de IA en segundo plano al arrancar"""
        if self.engine is None:
            try:
                print("⏳ Pre-cargando SmartFaceEngine en segundo plano...")
                self.engine = SmartFaceEngine()
                print("✅ Motor SmartFaceEngine listo.")
            except Exception as e:
                print(f"Error al pre-cargar SmartFaceEngine: {e}")
    
    def _pre_cargar_camara(self):
        """Inicializa la cámara en segundo plano"""
        if self.cap is None:
            try:
                print("⏳ Pre-cargando la cámara...")
                self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                print("✅ Cámara lista.")
            except Exception as e:
                print(f"Error al pre-cargar la cámara: {e}")

    # --------------------------------------------
    # LÓGICA DE ESCANEO Y HILO DE CÁMARA
    # --------------------------------------------
    def _start_scan(self, e):
        if self.scanning: 
            return
        self.scanning = True
        
        if self.engine:
            self.engine.reiniciar_sesion()
            self.engine.recargar_datos()
        
        self.camera_content.controls = [
            self.video_image,
            ft.ProgressRing(color=ACCENT_BLUE, width=40, height=40),
            ft.Text("Iniciando cámara y motor de IA...", size=16, weight=ft.FontWeight.W_500, color=TEXT_COLOR)
        ]
        self.update()

        threading.Thread(target=self._camera_loop, daemon=True).start()

    def _camera_loop(self):
        print("DEBUG: Iniciando hilo de cámara...")
        
        while self.engine is None and self.scanning:
            time.sleep(0.1)
            
        if not self.scanning:
            return
        
        cap = self.cap
        if cap is None or not cap.isOpened():
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
        if not cap.isOpened():
            print("ERROR CRÍTICO: No se pudo abrir la cámara.")
            self.scanning = False
            return

        self.video_image.visible = True
        self.camera_content.controls = [self.video_image]
        try:
            self.update()
        except Exception:
            pass

        print("DEBUG: Bucle de video en ejecución.")

        try:
            while self.scanning:
                ret, frame = cap.read()
                if not ret or frame is None:
                    print("DEBUG: Frame vacío de la cámara.")
                    time.sleep(0.05)
                    continue

                # Procesar frame mediante el motor de IA
                if self.engine:
                    frame_procesado = self.engine.procesar_frame(frame)
                else:
                    frame_procesado = frame

                # Codificar a JPG para Flet
                success, buffer = cv2.imencode('.jpg', frame_procesado, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if not success:
                    continue
                    
                img_base64 = base64.b64encode(buffer).decode('utf-8')
                
                self.video_image.src_base64 = img_base64
                try:
                    self.update()
                except Exception:
                    break

                # Verificar si se detectó un estudiante válido
                if self.engine:
                    estudiante = self.engine.obtener_ultimo_estudiante()
                    nombre = estudiante.get("nombre", "")
                    if nombre and nombre != "Esperando escaneo...":
                        print(f"DEBUG: ¡Reconocido con éxito: {nombre}!")
                        self.scanning = False
                        self._show_result(estudiante)
                        break
                
                time.sleep(0.02)
                
        except Exception as ex:
            print(f"EXCEPCIÓN EN BUCLE DE CÁMARA: {ex}")
        finally:
            print("DEBUG: Hilo de cámara finalizado.")

    def _show_result(self, estudiante):
        self.video_image.visible = False
        self._update_sidebar_student(estudiante)
        
        nombre = estudiante.get('nombre', 'Desconocido')
        btn_volver = crear_boton_gradiente("Volver a escanear", on_click=self._reset_scanner, height=40, width=200)

        self.camera_content.controls = [
            ft.Icon(ft.icons.CHECK_CIRCLE, size=60, color=ACCENT_BLUE),
            ft.Text(f"¡Identificado: {nombre}!", size=22, weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
            ft.Text(f"Cédula: {estudiante.get('cedula', 'N/A')}", size=14, color=TEXT_COLOR),
            btn_volver
        ]
        self.update()

    def _reset_scanner(self, e):
        if self.engine:
            self.engine.reiniciar_sesion()
            
        self.sidebar_content.controls = [
            ft.Icon(ft.icons.FACE_RETOUCHING_NATURAL, size=50, color=ACCENT_BLUE),
            ft.Text("SmartFace", size=20, weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
            ft.Container(height=20),
            ft.Icon(ft.icons.PERSON_SEARCH_OUTLINED, size=60, color=ACCENT_MID),
            ft.Text("Esperando escaneo...", size=16, weight=ft.FontWeight.W_500, color=TEXT_COLOR, text_align=ft.TextAlign.CENTER),
            ft.Text("Inicia el escaneo para ver los datos del estudiante.", size=12, color="#7F8C8D", text_align=ft.TextAlign.CENTER)
        ]
            
        self.video_image.visible = False
        btn_escanear = crear_boton_gradiente("Escanear", on_click=self._start_scan, height=40, width=200)

        self.camera_content.controls = [
            self.video_image,
            ft.Icon(ft.icons.VIDEOCAM_OUTLINED, size=80, color=ACCENT_MID),
            ft.Text("Cámara (Inactiva)", size=18, weight=ft.FontWeight.W_500, color=TEXT_COLOR),
            btn_escanear
        ]
        self.update()

# ============================================
# MAIN
# ============================================

def main(page: ft.Page):
    page.title = "SmartFace - Reconocimiento"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.bgcolor = BG_COLOR
    page.window_width = 1200
    page.window_height = 800
    
    app = UniversityApp(page)
    
    page.window_prevent_close = True
    def window_event(e):
        if e.data == "close":
            app.scanning = False
            if app.cap and app.cap.isOpened():
                app.cap.release()
            page.window_destroy()
            
    page.on_window_event = window_event
    page.add(app)
    page.update()

if __name__ == "__main__":
    ft.app(target=main)