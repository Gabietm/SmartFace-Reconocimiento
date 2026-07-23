"""
app.py - Aplicación para Flet 0.21.2 con Integración OpenCV + YOLO
Diseño Neumórfico
"""

import flet as ft
import time
import threading
import cv2
import base64

# Importamos tu motor de reconocimiento facial
from smartface_engine import SmartFaceEngine

# ============================================
# COLORES Y ESTILOS NEUMÓRFICOS
# ============================================

BG_COLOR = "#E0E5EC"
TEXT_COLOR = "#4A5A6E"
ACCENT_COLOR = "#2979FF"

def get_neumorphic_shadows():
    return [
        ft.BoxShadow(spread_radius=1, blur_radius=12, color="white", offset=ft.Offset(-6, -6)),
        ft.BoxShadow(spread_radius=1, blur_radius=12, color="#A3B1C6", offset=ft.Offset(6, 6))
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

# ============================================
# CLASE PRINCIPAL
# ============================================

class UniversityApp(ft.UserControl):
    
    def __init__(self):
        super().__init__()
        self.expand = True 
        self.active_tab = "Escaner"
        self.scanning = False
        self.engine = None  # Inicializaremos el motor de IA cuando se abra la app
        
        # Píxel transparente en Base64 para inicializar ft.Image sin errores en Flet 0.21.2
        self.transparent_pixel = (
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        )
        
        # Componente de imagen donde inyectaremos los frames de OpenCV
        self.video_image = ft.Image(
            src_base64=self.transparent_pixel,
            width=640,
            height=480,
            fit=ft.ImageFit.CONTAIN,
            border_radius=15,
            visible=False
        )
        
    def build(self):
        return ft.Container(
            bgcolor=BG_COLOR,
            expand=True,
            padding=ft.padding.all(30),
            content=ft.Row(
                expand=True,
                spacing=30,
                controls=[
                    self._build_sidebar(),
                    self._build_main_area()
                ]
            )
        )

    # --------------------------------------------
    # SIDEBAR
    # --------------------------------------------
    def _build_sidebar(self):
        return neu_container(
            width=250,
            padding=30,
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Icon(ft.icons.FACE_RETOUCHING_NATURAL, size=50, color=ACCENT_COLOR),
                    ft.Text("SmartFace", size=20, weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
                    ft.Container(height=40),
                    self._build_menu_button("Escaner", ft.icons.DOCUMENT_SCANNER),
                    ft.Container(height=10),
                    self._build_menu_button("Estudiantes", ft.icons.PEOPLE),
                ]
            )
        )

    def _build_menu_button(self, text, icon):
        is_active = self.active_tab == text
        color = ACCENT_COLOR if is_active else TEXT_COLOR
        return ft.Container(
            padding=ft.padding.symmetric(horizontal=20, vertical=15),
            border_radius=15,
            bgcolor=BG_COLOR if not is_active else "#D1D9E6",
            shadow=get_neumorphic_shadows() if not is_active else None,
            content=ft.Row(
                spacing=15,
                controls=[
                    ft.Icon(icon, color=color, size=22),
                    ft.Text(text, size=15, weight=ft.FontWeight.W_600, color=color)
                ]
            ),
            on_click=lambda e: self._change_tab(text)
        )

    def _change_tab(self, text):
        if self.active_tab != text:
            self.active_tab = text
            self.update()

    # --------------------------------------------
    # ÁREA PRINCIPAL
    # --------------------------------------------
    def _build_main_area(self):
        return ft.Column(
            expand=True,
            spacing=30,
            controls=[
                self._build_camera_section(),
                self._build_stats_section()
            ]
        )

    def _build_camera_section(self):
        self.camera_content = ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            controls=[
                self.video_image,
                ft.Icon(ft.icons.VIDEOCAM_OUTLINED, size=80, color=TEXT_COLOR),
                ft.Text("Cámara (Inactiva)", size=18, weight=ft.FontWeight.W_500, color=TEXT_COLOR),
                
                ft.Container(
                    margin=ft.padding.only(top=20),
                    content=ft.Text("Escanear", size=16, weight=ft.FontWeight.BOLD, color="white"),
                    bgcolor=ACCENT_COLOR,
                    padding=ft.padding.symmetric(horizontal=50, vertical=15),
                    border_radius=30,
                    shadow=[ft.BoxShadow(spread_radius=1, blur_radius=10, color=ACCENT_COLOR, offset=ft.Offset(0, 4))],
                    on_click=self._start_scan
                )
            ]
        )

        return neu_container(
            expand=True,
            content=ft.Container(
                alignment=ft.alignment.center,
                content=self.camera_content
            )
        )

    def _build_stats_section(self):
        pct_solv, pct_mor, total = 63, 37, 156 

        return ft.Row(
            height=200,
            spacing=30,
            controls=[
                neu_container(
                    shape=ft.BoxShape.CIRCLE, width=200,
                    content=self._build_circular_chart("Solvencia", pct_solv, "#00C853")
                ),
                neu_container(
                    shape=ft.BoxShape.CIRCLE, width=200,
                    content=self._build_circular_chart("Morosidad", pct_mor, "#FF1744")
                ),
                neu_container(
                    expand=True,
                    content=ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=5,
                        controls=[
                            ft.Text("Estudiantes registrados:", size=16, color=TEXT_COLOR),
                            ft.Text(str(total), size=48, weight=ft.FontWeight.BOLD, color=ACCENT_COLOR)
                        ]
                    )
                )
            ]
        )

    def _build_circular_chart(self, label, percentage, color):
        return ft.Stack(
            controls=[
                ft.Container(
                    alignment=ft.alignment.center,
                    content=ft.ProgressRing(
                        value=percentage / 100, color=color, bgcolor=BG_COLOR,
                        stroke_width=12, width=140, height=140
                    )
                ),
                ft.Container(
                    alignment=ft.alignment.center,
                    content=ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=0,
                        controls=[
                            ft.Text(f"{int(percentage)}%", size=28, weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
                            ft.Text(label, size=12, color=TEXT_COLOR)
                        ]
                    )
                )
            ]
        )

    # --------------------------------------------
    # LÓGICA DE INTEGRACIÓN CON OPENCV
    # --------------------------------------------
    def _start_scan(self, e):
        if self.scanning: return
        self.scanning = True
        
        self.camera_content.controls = [
            self.video_image,
            ft.Text("Iniciando motor YOLO y cámara...", size=16, weight=ft.FontWeight.W_500, color=TEXT_COLOR)
        ]
        self.update()

        threading.Thread(target=self._camera_loop, daemon=True).start()

    def _camera_loop(self):
        if self.engine is None:
            self.engine = SmartFaceEngine()
            
        cap = cv2.VideoCapture(0)
        self.video_image.visible = True
        self.camera_content.controls = [self.video_image]
        self.update()

        while self.scanning and cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            frame_procesado = self.engine.procesar_frame(frame)

            _, buffer = cv2.imencode('.jpg', frame_procesado)
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            self.video_image.src_base64 = img_base64
            self.update()

            estudiante = self.engine.obtener_ultimo_estudiante()
            
            if estudiante and estudiante.get("id") is not None:
                self.scanning = False
                self._show_result(estudiante)
                break
            
            time.sleep(0.03)

        cap.release()

    def _show_result(self, estudiante):
        self.video_image.visible = False
        
        es_activo = estudiante.get('es_activo', False)
        color_estado = "#00C853" if es_activo else "#FF1744"
        texto_estado = "Activo/Solvente" if es_activo else "Moroso/Inactivo"

        self.camera_content.controls = [
            ft.Icon(ft.icons.CHECK_CIRCLE, size=60, color=color_estado),
            ft.Text(f"¡Identificado: {estudiante.get('nombre', 'Desconocido')}!", size=22, weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
            ft.Text(f"Similitud: {estudiante.get('similitud', 0)*100:.1f}%", size=14, color=TEXT_COLOR),
            ft.Text(f"Estado: {texto_estado}", size=16, weight=ft.FontWeight.BOLD, color=color_estado),
            
            ft.Container(
                margin=ft.padding.only(top=15),
                content=ft.Text("Volver a escanear", size=14, weight=ft.FontWeight.BOLD, color="white"),
                bgcolor=TEXT_COLOR,
                padding=ft.padding.symmetric(horizontal=30, vertical=10),
                border_radius=20,
                on_click=self._reset_scanner
            )
        ]
        self.update()

    def _reset_scanner(self, e):
        self.video_image.visible = False
        self.camera_content.controls = [
            self.video_image,
            ft.Icon(ft.icons.VIDEOCAM_OUTLINED, size=80, color=TEXT_COLOR),
            ft.Text("Cámara (Inactiva)", size=18, weight=ft.FontWeight.W_500, color=TEXT_COLOR),
            ft.Container(
                margin=ft.padding.only(top=20),
                content=ft.Text("Escanear", size=16, weight=ft.FontWeight.BOLD, color="white"),
                bgcolor=ACCENT_COLOR,
                padding=ft.padding.symmetric(horizontal=50, vertical=15),
                border_radius=30,
                shadow=[ft.BoxShadow(spread_radius=1, blur_radius=10, color=ACCENT_COLOR, offset=ft.Offset(0, 4))],
                on_click=self._start_scan
            )
        ]
        self.update()
        
    def did_unmount(self):
        if self.engine:
            self.engine.cerrar()
        super().did_unmount()

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
    
    app = UniversityApp()
    page.add(app)
    page.update()

if __name__ == "__main__":
    ft.app(target=main)