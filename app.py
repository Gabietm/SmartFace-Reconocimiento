"""
app.py - Aplicación para Flet 0.21.2 con Integración OpenCV + YOLO
Diseño Neumórfico con Paleta Adobe Color & Gradiente Moderno
"""

import flet as ft
import time
import threading
import cv2
import base64
from smartface_engine import SmartFaceEngine
from bd import UniversityDatabase
from config import DB_PATH
import datetime
from tasa_bcv import MonitorBCV

# ============================================
# PALETA DE COLORES ADOBE COLOR
# ============================================

BG_COLOR = "#F2F2F2"       # Tono base extraído de la paleta
TEXT_COLOR = "#2C3E50"     # Gris oscuro sofisticado para texto
ACCENT_BLUE = "#353FF2"    # Azul vibrante principal
ACCENT_MID = "#3084F2"     # Azul intermedio
ACCENT_LIGHT = "#2E97F2"   # Azul claro / cyan

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

# ============================================
# CLASE PRINCIPAL
# ============================================

class UniversityApp(ft.UserControl):
    
    def __init__(self):
        super().__init__()
        self.expand = True 
        self.active_tab = "Escaner"
        self.scanning = False
        self.engine = None
        self.monitor_bcv = MonitorBCV()
        
        # Pre-cargar el motor de IA en segundo plano al abrir la app
        threading.Thread(target=self._pre_cargar_motor, daemon=True).start()
        
        # Píxel transparente en Base64 para evitar errores de inicialización
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
            width=280,
            padding=25,
            content=self.sidebar_content
        )
    
    def _update_sidebar_student(self, estudiante):
        """Actualiza la barra lateral con los datos detallados del estudiante reconocido"""
        es_activo = estudiante.get('es_activo', False)
        color_estado = ACCENT_BLUE if es_activo else "#FF1744"
        texto_estado = "Solvente" if es_activo else "Moroso / Inactivo"
        
        # 1. Obtener nombres y apellidos correctamente combinados
        nombres = estudiante.get('nombre') or estudiante.get('nombres', '')
        apellidos = estudiante.get('apellido') or estudiante.get('apellidos', '')
        nombre_completo = f"{nombres} {apellidos}".strip()
        if not nombre_completo:
            nombre_completo = estudiante.get('nombre', 'Desconocido')

        # 2. Buscar la foto utilizando estrictamente la Cédula en la carpeta "fotos_registros"
        cedula = str(estudiante.get('cedula', '')).strip()
        image_control = ft.Image(
            src_base64=self.transparent_pixel,
            width=110,
            height=110,
            fit=ft.ImageFit.COVER,
            border_radius=55
        )
        
        if cedula:
            import os
            extensiones = ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']
            ruta_encontrada = None
            
            for ext in extensiones:
                candidato = os.path.join("fotos_registros", f"{cedula}{ext}")
                posibles = [candidato, os.path.join(os.getcwd(), candidato), os.path.abspath(candidato)]
                
                for p in posibles:
                    if p and os.path.exists(p):
                        ruta_encontrada = p
                        break
                if ruta_encontrada:
                    break
            
            if ruta_encontrada:
                try:
                    with open(ruta_encontrada, "rb") as f_img:
                        b64_img = base64.b64encode(f_img.read()).decode('utf-8')
                        image_control.src_base64 = b64_img
                except Exception as e:
                    print(f"Error al leer la foto con cédula {cedula}: {e}")

        cuota = estudiante.get('cuota_pendiente', 'Cuota de Inscripción')
        precio_euro = estudiante.get('precio_euro', 0.0)
        precio_bs = estudiante.get('precio_bs', 0.0)

        info_controls = [
            ft.Container(
                content=image_control,
                border=ft.border.all(3, color_estado),
                border_radius=60,
                padding=2
            ),
            ft.Column([
                ft.Text("Estudiante", size=11, color="#7F8C8D", weight=ft.FontWeight.BOLD),
                ft.Text(nombre_completo, size=15, weight=ft.FontWeight.BOLD, color=TEXT_COLOR, text_align=ft.TextAlign.CENTER)
            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Row([
                ft.Icon(ft.icons.BADGE_OUTLINED, size=16, color=ACCENT_MID),
                ft.Text(f"Cédula: {cedula or 'N/A'}", size=13, color=TEXT_COLOR)
            ], spacing=8),
            ft.Row([
                ft.Icon(ft.icons.SCHOOL_OUTLINED, size=16, color=ACCENT_MID),
                ft.Text(f"Carrera: {estudiante.get('carrera', 'N/A')}", size=13, color=TEXT_COLOR)
            ], spacing=8),
            ft.Row([
                ft.Icon(ft.icons.TIMELINE, size=16, color=ACCENT_MID),
                ft.Text(f"Semestre: {estudiante.get('semestre', 'N/A')}", size=13, color=TEXT_COLOR)
            ], spacing=8),
            ft.Divider(height=1, color="#D0D5DD")
        ]

        solvencia_controls = [
            ft.Row([
                ft.Icon(ft.icons.VERIFIED_USER_OUTLINED, size=16, color=color_estado),
                ft.Text(f"Estado: {texto_estado}", size=13, weight=ft.FontWeight.BOLD, color=color_estado)
            ], spacing=8)
        ]

        if not es_activo:
            solvencia_controls.append(
                ft.Container(
                    bgcolor="#FDEDEC",
                    padding=10,
                    border_radius=10,
                    content=ft.Column([
                        ft.Text("Deuda pendiente:", size=11, weight=ft.FontWeight.BOLD, color="#C0392B"),
                        ft.Text(f"• {cuota}", size=12, color=TEXT_COLOR),
                        ft.Text(f"• 🇪🇺 €{precio_euro:.2f}", size=12, weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
                        ft.Text(f"• 🇻🇪 Bs. {precio_bs:.2f}", size=12, weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
                    ], spacing=2)
                )
            )

        info_controls.extend(solvencia_controls)
        info_controls.append(
            ft.Container(
                margin=ft.margin.only(top=5),
                content=ft.Row([
                    ft.Icon(ft.icons.CHECK_CIRCLE if es_activo else ft.icons.WARNING_AMBER_ROUNDED, size=28, color=color_estado),
                    ft.Text("Verificado por SmartFace", size=11, color="#7F8C8D", italic=True)
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=5)
            )
        )

        self.sidebar_content.controls = info_controls
        self.update()

    # --------------------------------------------
    # ÁREA PRINCIPAL
    # --------------------------------------------
    def _build_main_area(self):
        self.stats_section = self._build_stats_section()
        return ft.Column(
            expand=True,
            spacing=30,
            controls=[
                self._build_camera_section(),
                self.stats_section
            ]
        )
        
    def _build_stats_section(self):
        total = 0
        pct_solv = 0
        pct_mor = 0

        try:
            db = UniversityDatabase(DB_PATH)
            estudiantes = db.obtener_todos_estudiantes()
            total = len(estudiantes)
            
            if total > 0:
                fecha_hoy = datetime.date.today().strftime('%Y-%m-%d')
                periodo_activo_id = None
                
                # Obtener periodo activo
                with db._get_connection() as conn:
                    p_cursor = conn.execute("SELECT id FROM periodos WHERE activo = 1 LIMIT 1")
                    p_row = p_cursor.fetchone()
                    if p_row:
                        periodo_activo_id = p_row['id'] if hasattr(p_row, 'keys') else p_row[0]

                activos = 0
                for est in estudiantes:
                    est_id = est['id'] if hasattr(est, 'keys') else est[0]
                    es_solvente = True
                    
                    if periodo_activo_id:
                        with db._get_connection() as conn:
                            # Buscar cuotas vencidas
                            c_cursor = conn.execute(
                                "SELECT id FROM cuotas WHERE periodo_id = ? AND fecha_vencimiento <= ?",
                                (periodo_activo_id, fecha_hoy)
                            )
                            cuotas_vencidas = c_cursor.fetchall()
                            
                            if cuotas_vencidas:
                                ids_cuotas_vencidas = [row['id'] if hasattr(row, 'keys') else row[0] for row in cuotas_vencidas]
                                placeholders = ','.join(['?'] * len(ids_cuotas_vencidas))
                                
                                # Verificar si el estudiante pagó esas cuotas
                                p_cursor = conn.execute(
                                    f"""SELECT DISTINCT cuota_id FROM pagos 
                                       WHERE estudiante_id = ? AND cuota_id IN ({placeholders})""",
                                    [est_id] + ids_cuotas_vencidas
                                )
                                pagos_vencidos = p_cursor.fetchall()
                                ids_pagados = {row['cuota_id'] if hasattr(row, 'keys') else row[0] for row in pagos_vencidos}
                                
                                for c_id in ids_cuotas_vencidas:
                                    if c_id not in ids_pagados:
                                        es_solvente = False
                                        break
                    
                    if es_solvente:
                        activos += 1

                inactivos = total - activos
                pct_solv = (activos / total) * 100
                pct_mor = (inactivos / total) * 100
        except Exception as e:
            print(f"Error al cargar estadísticas: {e}")

        return ft.Row(
            height=200,
            spacing=30,
            controls=[
                neu_container(shape=ft.BoxShape.CIRCLE, width=200, content=self._build_circular_chart("Solvencia", pct_solv, ACCENT_BLUE)),
                neu_container(shape=ft.BoxShape.CIRCLE, width=200, content=self._build_circular_chart("Morosidad", pct_mor, "#FF1744")),
                neu_container(
                    expand=True,
                    content=ft.Column(
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=5,
                        controls=[
                            ft.Text("Estudiantes registrados:", size=16, color=TEXT_COLOR),
                            ft.Text(str(total), size=48, weight=ft.FontWeight.BOLD, color=ACCENT_BLUE)
                        ]
                    )
                )
            ]
        )
    
    def _build_camera_section(self):
        self.camera_content = ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=20,
            controls=[
                self.video_image,
                ft.Icon(ft.icons.VIDEOCAM_OUTLINED, size=80, color=ACCENT_MID),
                ft.Text("Cámara (Inactiva)", size=18, weight=ft.FontWeight.W_500, color=TEXT_COLOR),
                
                ft.Container(
                    margin=ft.margin.only(top=20),
                    content=ft.Text("Escanear", size=16, weight=ft.FontWeight.BOLD, color="white"),
                    gradient=GRADIENT_MODERNO,
                    padding=ft.padding.symmetric(horizontal=50, vertical=15),
                    border_radius=30,
                    shadow=[ft.BoxShadow(spread_radius=1, blur_radius=12, color="#353FF2", offset=ft.Offset(0, 5))],
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
    
    def _pre_cargar_motor(self):
        """Inicializa el motor YOLO e InsightFace de forma silenciosa al arrancar la app"""
        if self.engine is None:
            try:
                print("⏳ Pre-cargando motor de IA en segundo plano...")
                self.engine = SmartFaceEngine()
                print("✅ Motor de IA pre-cargado y listo para usar.")
            except Exception as e:
                print(f"Error al pre-cargar el motor de IA: {e}")

    # --------------------------------------------
    # LÓGICA DE INTEGRACIÓN CON OPENCV
    # --------------------------------------------
    def _start_scan(self, e):
        if self.scanning: return
        self.scanning = True
        
        if self.engine:
            self.engine.reiniciar_sesion()
            self.engine.recargar_datos()
        
        self.camera_content.controls = [
            self.video_image,
            ft.ProgressRing(color=ACCENT_BLUE, width=40, height=40),
            ft.Text("Iniciando motor YOLO y cámara...", size=16, weight=ft.FontWeight.W_500, color=TEXT_COLOR)
        ]
        self.update()

        threading.Thread(target=self._camera_loop, daemon=True).start()

    def _camera_loop(self):
        # Si el motor aún se está cargando en segundo plano, esperamos de forma fluida
        while self.engine is None and self.scanning:
            time.sleep(0.1)
            
        if not self.scanning:
            return
            
        # 🚀 Optimización 1: Usar DirectShow (en Windows) y fijar resolución ligera para apertura inmediata
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.video_image.visible = True
        self.camera_content.controls = [self.video_image]
        try:
            self.update()
        except Exception:
            pass

        frame_count = 0
        frame_procesado = None

        while self.scanning and cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            frame_count += 1

            # 🚀 Optimización 2: Frame Skipping. 
            # La IA procesa fotogramas alternos (ej. uno sí, uno no) para garantizar máxima fluidez visual.
            if frame_count % 2 == 0:
                frame_procesado = self.engine.procesar_frame(frame)
            elif frame_procesado is not None:
                # Mantenemos el frame procesado anterior temporalmente para evitar parpadeos
                pass
            else:
                frame_procesado = frame

            # Codificar y enviar a la interfaz gráfica de Flet con alta velocidad
            _, buffer = cv2.imencode('.jpg', frame_procesado, [cv2.IMWRITE_JPEG_QUALITY, 80])
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            self.video_image.src_base64 = img_base64
            try:
                self.update()
            except Exception:
                break

            estudiante = self.engine.obtener_ultimo_estudiante()
            
            if estudiante and estudiante.get("id") is not None:
                self.scanning = False
                self._show_result(estudiante)
                break
            
            time.sleep(0.01) # Reducido ligeramente para dar mayor fluidez al hilo gráfico

        cap.release()

    def _show_result(self, estudiante):
        self.video_image.visible = False
        estudiante_completo = estudiante.copy()
        
        try:
            db = UniversityDatabase(DB_PATH)
            todos_los_estudiantes = db.obtener_todos_estudiantes()
            
            est_id = estudiante.get('id')
            est_nombre = estudiante.get('nombre')
            
            reg_encontrado = None
            for reg in todos_los_estudiantes:
                if (est_id is not None and str(reg.get('id')) == str(est_id)) or (reg.get('nombre') == est_nombre):
                    reg_encontrado = reg
                    break
            
            if reg_encontrado:
                estudiante_completo.update(reg_encontrado)
                est_id_real = reg_encontrado.get('id')
                
                # CÁLCULO DINÁMICO DE SOLVENCIA PARA EL ESTUDIANTE RECONOCIDO
                fecha_hoy = datetime.date.today().strftime('%Y-%m-%d')
                periodo_activo_id = None
                
                with db._get_connection() as conn:
                    p_cursor = conn.execute("SELECT id FROM periodos WHERE activo = 1 LIMIT 1")
                    p_row = p_cursor.fetchone()
                    if p_row:
                        periodo_activo_id = p_row['id'] if hasattr(p_row, 'keys') else p_row[0]

                es_solvente = True
                if periodo_activo_id and est_id_real:
                    # Obtener la tasa del día automáticamente mediante el script MonitorBCV
                    tasa_euro = self.monitor_bcv.obtener_precio_euro()
                    
                    with db._get_connection() as conn:
                        # Usamos SELECT * para evitar errores de columnas faltantes y adaptarnos al esquema de bd
                        c_cursor = conn.execute(
                            "SELECT * FROM cuotas WHERE periodo_id = ? AND fecha_vencimiento <= ?",
                            (periodo_activo_id, fecha_hoy)
                        )
                        cuotas_vencidas = c_cursor.fetchall()
                        
                        if cuotas_vencidas:
                            ids_cuotas_vencidas = [row['id'] if hasattr(row, 'keys') else row[0] for row in cuotas_vencidas]
                            placeholders = ','.join(['?'] * len(ids_cuotas_vencidas))
                            
                            p_cursor = conn.execute(
                                f"""SELECT DISTINCT cuota_id FROM pagos 
                                   WHERE estudiante_id = ? AND cuota_id IN ({placeholders})""",
                                [est_id_real] + ids_cuotas_vencidas
                            )
                            pagos_vencidos = p_cursor.fetchall()
                            ids_pagados = {row['cuota_id'] if hasattr(row, 'keys') else row[0] for row in pagos_vencidos}
                            
                            for c in cuotas_vencidas:
                                c_id = c['id'] if hasattr(c, 'keys') else c[0]
                                if c_id not in ids_pagados:
                                    es_solvente = False
                                    
                                    # Mapeo seguro de columnas por si varían en la base de datos
                                    keys = c.keys() if hasattr(c, 'keys') else []
                                    
                                    c_nombre = 'Cuota Pendiente'
                                    for k in ['nombre', 'descripcion', 'concepto', 'titulo']:
                                        if k in keys:
                                            c_nombre = c[k]
                                            break
                                            
                                    c_euro = 0.0
                                    for k in ['monto_euro', 'precio_euro', 'monto', 'euro']:
                                        if k in keys:
                                            c_euro = c[k]
                                            break
                                            
                                    # Cálculo exacto de la equivalencia en bolívares multiplicando los euros de la BD por la tasa BCV
                                    c_bs = c_euro * tasa_euro if tasa_euro > 0 else 0.0
                                    
                                    estudiante_completo['cuota_pendiente'] = c_nombre
                                    estudiante_completo['precio_euro'] = c_euro
                                    estudiante_completo['precio_bs'] = c_bs
                                    break
                
                estudiante_completo['es_activo'] = es_solvente

        except Exception as e:
            print(f"Error al consultar la BD para el perfil lateral: {e}")

        # Actualizar la barra lateral con los datos dinámicos calculados
        self._update_sidebar_student(estudiante_completo)
        
        es_activo = estudiante_completo.get('es_activo', False)
        color_estado = ACCENT_BLUE if es_activo else "#FF1744"
        texto_estado = "Activo/Solvente" if es_activo else "Moroso/Inactivo"

        self.camera_content.controls = [
            ft.Icon(ft.icons.CHECK_CIRCLE, size=60, color=color_estado),
            ft.Text(f"¡Identificado: {estudiante_completo.get('nombre', 'Desconocido')}!", size=22, weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
            ft.Text(f"Similitud: {estudiante_completo.get('similitud', 0)*100:.1f}%", size=14, color=TEXT_COLOR),
            ft.Text(f"Estado: {texto_estado}", size=16, weight=ft.FontWeight.BOLD, color=color_estado),
            
            ft.Container(
                margin=ft.margin.only(top=15),
                content=ft.Text("Volver a escanear", size=14, weight=ft.FontWeight.BOLD, color="white"),
                gradient=GRADIENT_MODERNO,
                padding=ft.padding.symmetric(horizontal=30, vertical=10),
                border_radius=20,
                shadow=[ft.BoxShadow(spread_radius=1, blur_radius=8, color="#353FF2", offset=ft.Offset(0, 3))],
                on_click=self._reset_scanner
            )
        ]
        
        # Refrescar estadísticas del panel inferior
        new_stats = self._build_stats_section()
        self.stats_section.controls = new_stats.controls
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
        self.camera_content.controls = [
            self.video_image,
            ft.Icon(ft.icons.VIDEOCAM_OUTLINED, size=80, color=ACCENT_MID),
            ft.Text("Cámara (Inactiva)", size=18, weight=ft.FontWeight.W_500, color=TEXT_COLOR),
            ft.Container(
                margin=ft.margin.only(top=20),
                content=ft.Text("Escanear", size=16, weight=ft.FontWeight.BOLD, color="white"),
                gradient=GRADIENT_MODERNO,
                padding=ft.padding.symmetric(horizontal=50, vertical=15),
                border_radius=30,
                shadow=[ft.BoxShadow(spread_radius=1, blur_radius=12, color="#353FF2", offset=ft.Offset(0, 5))],
                on_click=self._start_scan
            )
        ]
        
        new_stats = self._build_stats_section()
        self.stats_section.controls = new_stats.controls
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
    
    page.window_prevent_close = True
    def window_event(e):
        if e.data == "close":
            if app.engine:
                app.engine.cerrar()
            page.window_destroy()
            
    page.on_window_event = window_event
    
    page.add(app)
    page.update()

if __name__ == "__main__":
    ft.app(target=main)