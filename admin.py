"""
admin.py - Panel de Administración y Control Unificado (SmartFace Pro)
Conectado a la base de datos (bd.py) con Navegación Lateral (NavigationRail)
"""

import os
import cv2
import base64
import threading
import json
import datetime
import numpy as np
import flet as ft
from bd import UniversityDatabase  # Importación de tu base de datos en bd.py
from tasa_bcv import MonitorBCV
from config import FOTOS_DIR

try:
    from _registrar_usuario import procesar_y_guardar_usuario
except ImportError:
    procesar_y_guardar_usuario = None

BG_COLOR = "#F2F2F2"
TEXT_COLOR = "#2C3E50"
ACCENT_BLUE = "#353FF2"
ACCENT_MID = "#3084F2"

GRADIENT_MODERNO = ft.LinearGradient(
    begin=ft.alignment.top_left,
    end=ft.alignment.bottom_right,
    colors=["#353FF2", "#3565F2", "#3084F2", "#3097F2"]
)

def get_neumorphic_shadows():
    return [
        ft.BoxShadow(spread_radius=1, blur_radius=10, color="white", offset=ft.Offset(-5, -5)),
        ft.BoxShadow(spread_radius=1, blur_radius=10, color="#D0D5DD", offset=ft.Offset(5, 5))
    ]

def neu_container(content=None, padding=20, border_radius=20, expand=False, width=None, height=None):
    return ft.Container(
        content=content, padding=padding,
        border_radius=border_radius, bgcolor=BG_COLOR,
        width=width, height=height, expand=expand,
        shadow=get_neumorphic_shadows(),
        animate=ft.animation.Animation(300, ft.AnimationCurve.EASE_OUT)
    )

class SmartFaceDashboard(ft.UserControl):
    def __init__(self):
        super().__init__()
        self.expand = True
        self.current_index = 0
        self.scanning = False
        self.current_frame = None
        self.editing_cedula = None 
        self.monitor_bcv = MonitorBCV()
        
        try:
            self.db = UniversityDatabase()
        except Exception as e:
            print(f"Error al conectar con la BD: {e}")
            self.db = None

        # --- Componentes para Vista de Estudiantes ---
        self.txt_cedula = self._neu_text_field("Cédula / Identificación", ft.icons.BADGE_OUTLINED)
        self.txt_nombre = self._neu_text_field("Nombres", ft.icons.PERSON_OUTLINE)
        self.txt_apellido = self._neu_text_field("Apellidos", ft.icons.PERSON_OUTLINE)
        self.txt_email = self._neu_text_field("Correo Electrónico", ft.icons.EMAIL_OUTLINED)
        
        # Menú desplegable para Carrera / Especialidad
        carreras_disponibles = [
            "Ingeniería en Sistemas",
            "Ingeniería Civil",
            "Ingeniería Industrial",
            "Ingeniería Electrónica",
            "Ingeniería Electrica",
            "Ingeniería de Mantenimiento Mecanico",
            "Arquitectura",
        ]
        self.dd_carrera = ft.Dropdown(
            label="Carrera",
            prefix_icon=ft.icons.SCHOOL_OUTLINED,
            border=ft.InputBorder.NONE,
            filled=True,
            bgcolor=BG_COLOR,
            color=TEXT_COLOR,
            label_style=ft.TextStyle(color=TEXT_COLOR),
            border_radius=15,
            focused_border_color=ACCENT_BLUE,
            options=[ft.dropdown.Option(c) for c in carreras_disponibles]
        )
        
        self.txt_semestre = self._neu_text_field("Semestre", ft.icons.FORMAT_LIST_BULLETED)
        
        # Barra de búsqueda por cédula para la lista de estudiantes
        self.txt_buscar_estudiante = ft.TextField(
            label="Buscar por Cédula",
            prefix_icon=ft.icons.SEARCH,
            border_radius=15,
            bgcolor=BG_COLOR,
            color=TEXT_COLOR,
            label_style=ft.TextStyle(color=TEXT_COLOR),
            on_change=self.cargar_estudiantes,
            expand=True
        )
        
        self.transparent_pixel = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
        self.video_image = ft.Image(
            src_base64=self.transparent_pixel,
            width=320, height=240,
            fit=ft.ImageFit.CONTAIN,
            border_radius=15,
            visible=False
        )
        
        self.status_text = ft.Text("Estado: Esperando acción...", size=13, color=TEXT_COLOR)
        self.lista_estudiantes = ft.ListView(expand=True, spacing=10)

        self.btn_accion_texto = ft.Text("Capturar y Guardar Estudiante", size=15, weight=ft.FontWeight.BOLD, color="white")
        self.btn_accion_container = ft.Container(
            alignment=ft.alignment.center,
            content=self.btn_accion_texto,
            gradient=GRADIENT_MODERNO,
            padding=ft.padding.symmetric(vertical=15),
            border_radius=20,
            shadow=[ft.BoxShadow(spread_radius=1, blur_radius=8, color="#353FF2", offset=ft.Offset(0, 4))],
            on_click=self._procesar_accion_principal
        )

        self.btn_cancelar = ft.TextButton(
            "Cancelar Edición",
            icon=ft.icons.CANCEL,
            icon_color="#FF1744",
            visible=False,
            on_click=self._limpiar_formulario
        )

        self.txt_total_count = ft.Text("0", size=16, weight=ft.FontWeight.BOLD, color=ACCENT_BLUE)
        self.txt_solventes_count = ft.Text("0", size=16, weight=ft.FontWeight.BOLD, color="#2E7D32")
        self.txt_morosos_count = ft.Text("0", size=16, weight=ft.FontWeight.BOLD, color="#C62828")

        # Contenedor principal dinámico para las vistas del menú
        self.content_area = ft.Container(expand=True, padding=20)
        self.actualizar_vista_contenido()

    def _neu_text_field(self, label, icon, expand=False):
        return ft.TextField(
            label=label,
            prefix_icon=icon,
            border=ft.InputBorder.NONE,
            filled=True,
            bgcolor=BG_COLOR,
            color=TEXT_COLOR,
            label_style=ft.TextStyle(color=TEXT_COLOR),
            border_radius=15,
            focused_border_color=ACCENT_BLUE,
            expand=expand
        )

    def _crear_campo_fecha_con_picker(self, label, icon):
        txt = self._neu_text_field(label, icon, expand=True)
        txt.read_only = True
        
        dp = ft.DatePicker(
            on_change=lambda e: setattr(txt, 'value', e.control.value.strftime('%Y-%m-%d') if e.control.value else '') or txt.update()
        )
        
        def mostrar_picker(e):
            if dp not in e.page.overlay:
                e.page.overlay.append(dp)
            dp.open = True
            e.page.update()

        btn = ft.IconButton(
            icon=ft.icons.CALENDAR_MONTH,
            icon_color=ACCENT_BLUE,
            tooltip="Seleccionar fecha",
            on_click=mostrar_picker
        )
        return txt, ft.Row([txt, btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def build(self):
        self.rail = ft.NavigationRail(
            selected_index=self.current_index,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=90,
            min_extended_width=180,
            bgcolor=BG_COLOR,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.icons.PEOPLE_OUTLINE,
                    selected_icon=ft.icons.PEOPLE,
                    label="Estudiantes",
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
                    selected_icon=ft.icons.ACCOUNT_BALANCE_WALLET,
                    label="Finanzas",
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.CALENDAR_MONTH_OUTLINED,
                    selected_icon=ft.icons.CALENDAR_MONTH,
                    label="Periodos y Cuotas",
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.ASSIGNMENT_OUTLINED,
                    selected_icon=ft.icons.ASSIGNMENT,
                    label="Logs & Accesos",
                ),
            ],
            on_change=self.on_nav_change,
        )

        return ft.Row(
            expand=True,
            spacing=0,
            controls=[
                self.rail,
                ft.VerticalDivider(width=1, color="#D0D5DD"),
                self.content_area
            ]
        )

    def on_nav_change(self, e):
        self.current_index = e.control.selected_index
        if self.current_index != 0:
            self.scanning = False
        self.actualizar_vista_contenido()
        self.update()

    def actualizar_vista_contenido(self):
        if not self.db:
            self.content_area.content = ft.Text("Error: No se pudo conectar a la base de datos.", color="#FF1744")
            return

        if self.current_index == 0:
            self.content_area.content = self.vista_estudiantes()
            threading.Thread(target=self.cargar_estudiantes, daemon=True).start()
        elif self.current_index == 1:
            self.content_area.content = self.vista_finanzas()
        elif self.current_index == 2:
            self.content_area.content = self.vista_periodos_cuotas()
        elif self.current_index == 3:
            self.content_area.content = self.vista_logs()

    # ==========================================
    # VISTA 1: GESTIÓN DE ESTUDIANTES Y BIOMETRÍA
    # ==========================================
    def vista_estudiantes(self):
        bottom_stats_bar = neu_container(
            height=70,
            padding=10,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                controls=[
                    ft.Row(spacing=8, controls=[
                        ft.Icon(ft.icons.GROUP, color=ACCENT_BLUE, size=18),
                        ft.Column(spacing=0, controls=[ft.Text("Registrados", size=10, color="#64748B"), self.txt_total_count])
                    ]),
                    ft.VerticalDivider(color="#D0D5DD"),
                    ft.Row(spacing=8, controls=[
                        ft.Icon(ft.icons.VERIFIED, color="#2E7D32", size=18),
                        ft.Column(spacing=0, controls=[ft.Text("Solventes", size=10, color="#64748B"), self.txt_solventes_count])
                    ]),
                    ft.VerticalDivider(color="#D0D5DD"),
                    ft.Row(spacing=8, controls=[
                        ft.Icon(ft.icons.WARNING_AMBER, color="#C62828", size=18),
                        ft.Column(spacing=0, controls=[ft.Text("Morosos", size=10, color="#64748B"), self.txt_morosos_count])
                    ])
                ]
            )
        )

        return ft.Column(
            expand=True,
            spacing=15,
            controls=[
                ft.Text("Gestión de Estudiantes y Biometría", size=22, weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
                ft.Divider(color="#D0D5DD"),
                ft.Row(
                    expand=True,
                    spacing=20,
                    controls=[
                        neu_container(
                            width=400,
                            padding=20,
                            content=ft.Column(
                                scroll=ft.ScrollMode.AUTO,
                                spacing=12,
                                controls=[
                                    ft.Row(
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                        controls=[
                                            ft.Row([
                                                ft.Icon(ft.icons.PERSON_ADD_ALT_1, color=ACCENT_BLUE, size=20),
                                                ft.Text("Formulario Estudiante", size=15, weight=ft.FontWeight.BOLD, color=TEXT_COLOR)
                                            ]),
                                            self.btn_cancelar
                                        ]
                                    ),
                                    self.txt_cedula,
                                    self.txt_nombre,
                                    self.txt_apellido,
                                    self.txt_email,
                                    self.dd_carrera,
                                    self.txt_semestre,
                                    ft.Divider(color="#D0D5DD"),
                                    ft.Column(
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                        spacing=8,
                                        controls=[
                                            self.video_image,
                                            self.status_text,
                                            ft.ElevatedButton(
                                                "Encender Cámara",
                                                icon=ft.icons.CAMERA_ALT,
                                                color="white",
                                                bgcolor=ACCENT_BLUE,
                                                on_click=self._toggle_camera
                                            )
                                        ]
                                    ),
                                    ft.Container(height=5),
                                    self.btn_accion_container
                                ]
                            )
                        ),
                        neu_container(
                            expand=True,
                            padding=20,
                            content=ft.Column(
                                expand=True,
                                spacing=15,
                                controls=[
                                    ft.Row(
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                        controls=[
                                            ft.Text("Estudiantes Registrados", size=18, weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
                                            ft.IconButton(icon=ft.icons.REFRESH, icon_color=TEXT_COLOR, tooltip="Actualizar lista", on_click=lambda e: threading.Thread(target=self.cargar_estudiantes, daemon=True).start())
                                        ]
                                    ),
                                    # Barra de búsqueda integrada por cédula
                                    ft.Row(
                                        controls=[
                                            self.txt_buscar_estudiante,
                                            ft.IconButton(
                                                icon=ft.icons.CLEAR,
                                                icon_color=TEXT_COLOR,
                                                tooltip="Limpiar búsqueda",
                                                on_click=self._limpiar_busqueda_estudiantes
                                            )
                                        ],
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                        spacing=10
                                    ),
                                    self.lista_estudiantes,
                                    bottom_stats_bar
                                ]
                            )
                        )
                    ]
                )
            ]
        )

    def _limpiar_busqueda_estudiantes(self, e):
        self.txt_buscar_estudiante.value = ""
        self.txt_buscar_estudiante.update()
        self.cargar_estudiantes()

    def cargar_estudiantes(self, e=None):
        if not self.db:
            return
        try:
            estudiantes_todos = self.db.obtener_todos_estudiantes()
            
            # Filtrar por cédula si hay texto escrito en el buscador
            filtro_cedula = self.txt_buscar_estudiante.value.strip().lower() if hasattr(self, 'txt_buscar_estudiante') and self.txt_buscar_estudiante.value else ""
            
            if filtro_cedula:
                estudiantes = [est for est in estudiantes_todos if filtro_cedula in str(est.get("cedula", "")).lower()]
            else:
                estudiantes = estudiantes_todos

            self.lista_estudiantes.controls.clear()
            
            total = len(estudiantes_todos)
            solventes = 0
            morosos = 0

            fecha_hoy = datetime.date.today().strftime('%Y-%m-%d')
            periodo_activo_id = None
            with self.db._get_connection() as conn:
                p_cursor = conn.execute("SELECT id FROM periodos WHERE activo = 1 LIMIT 1")
                p_row = p_cursor.fetchone()
                if p_row:
                    periodo_activo_id = p_row['id'] if hasattr(p_row, 'keys') else p_row[0]

            # Calcular solventes y morosos basados en el total general del sistema
            for est in estudiantes_todos:
                est_id = est['id'] if hasattr(est, 'keys') else est[0]
                es_solvente = True
                if periodo_activo_id:
                    with self.db._get_connection() as conn:
                        c_cursor = conn.execute(
                            "SELECT id FROM cuotas WHERE periodo_id = ? AND fecha_vencimiento <= ?",
                            (periodo_activo_id, fecha_hoy)
                        )
                        cuotas_vencidas = c_cursor.fetchall()
                        
                        if cuotas_vencidas:
                            ids_cuotas_vencidas = [row['id'] if hasattr(row, 'keys') else row[0] for row in cuotas_vencidas]
                            placeholders = ','.join(['?'] * len(ids_cuotas_vencidas))
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
                    solventes += 1
                else:
                    morosos += 1

            # Renderizar los estudiantes filtrados en la lista visual
            for est in estudiantes:
                est_id = est['id'] if hasattr(est, 'keys') else est[0]
                cedula = est["cedula"]
                nombre_completo = f"{est['nombre']} {est['apellido']}"
                carrera = est.get("carrera", "N/D")

                # Comprobar su solvencia individual para la etiqueta visual
                es_solvente = True
                if periodo_activo_id:
                    with self.db._get_connection() as conn:
                        c_cursor = conn.execute(
                            "SELECT id FROM cuotas WHERE periodo_id = ? AND fecha_vencimiento <= ?",
                            (periodo_activo_id, fecha_hoy)
                        )
                        cuotas_vencidas = c_cursor.fetchall()
                        if cuotas_vencidas:
                            ids_cuotas_vencidas = [row['id'] if hasattr(row, 'keys') else row[0] for row in cuotas_vencidas]
                            placeholders = ','.join(['?'] * len(ids_cuotas_vencidas))
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
                    estado_str = "Solvente"
                    color_badge = ACCENT_BLUE
                else:
                    estado_str = "Moroso"
                    color_badge = "#FF1744"

                self.lista_estudiantes.controls.append(
                    ft.Container(
                        padding=10,
                        border_radius=10,
                        bgcolor=BG_COLOR,
                        shadow=get_neumorphic_shadows(),
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Row(
                                    spacing=10,
                                    controls=[
                                        ft.CircleAvatar(content=ft.Text(est["nombre"][0], color="white", weight=ft.FontWeight.BOLD), bgcolor=ACCENT_MID),
                                        ft.Column(
                                            spacing=2,
                                            controls=[
                                                ft.Text(nombre_completo, size=13, weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
                                                ft.Text(f"Cédula: {cedula} | Carrera: {carrera}", size=11, color="#64748B")
                                            ]
                                        )
                                    ]
                                ),
                                ft.Row(
                                    spacing=5,
                                    controls=[
                                        ft.Container(
                                            padding=ft.padding.symmetric(horizontal=6, vertical=3),
                                            border_radius=6,
                                            bgcolor=color_badge,
                                            content=ft.Text(estado_str, size=10, weight=ft.FontWeight.BOLD, color="white")
                                        ),
                                        ft.IconButton(
                                            icon=ft.icons.EDIT_OUTLINED,
                                            icon_color=ACCENT_BLUE,
                                            icon_size=16,
                                            tooltip="Editar Estudiante",
                                            on_click=lambda e, s=est: self._preparar_edicion(s)
                                        ),
                                        ft.IconButton(
                                            icon=ft.icons.DELETE_OUTLINE,
                                            icon_color="#FF1744",
                                            icon_size=16,
                                            tooltip="Eliminar Estudiante",
                                            on_click=lambda e, c=cedula, nom=nombre_completo: self._confirmar_eliminar_estudiante(c, nom)
                                        )
                                    ]
                                )
                            ]
                        )
                    )
                )

            self.txt_total_count.value = str(total)
            self.txt_solventes_count.value = str(solventes)
            self.txt_morosos_count.value = str(morosos)
            
            self.update()
        except Exception as e:
            print(f"Error cargando estudiantes: {e}")

    def _preparar_edicion(self, est):
        self.editing_cedula = str(est["cedula"])
        self.txt_cedula.value = str(est["cedula"])
        self.txt_cedula.disabled = True  
        self.txt_nombre.value = est.get("nombre", "")
        self.txt_apellido.value = est.get("apellido", "")
        self.txt_email.value = est.get("email", "")
        self.txt_carrera.value = est.get("carrera", "")
        self.txt_semestre.value = str(est.get("semestre", 1))
        
        self.btn_accion_texto.value = "Actualizar Estudiante"
        self.btn_cancelar.visible = True
        self.status_text.value = f"Editando a: {est['nombre']}"
        self.update()

    def _limpiar_formulario(self, e=None):
        self.editing_cedula = None
        self.txt_cedula.value = ""
        self.txt_cedula.disabled = False
        self.txt_nombre.value = ""
        self.txt_apellido.value = ""
        self.txt_email.value = ""
        self.txt_carrera.value = ""
        self.txt_semestre.value = ""
        self.video_image.visible = False
        self.scanning = False
        
        self.btn_accion_texto.value = "Capturar y Guardar Estudiante"
        self.btn_cancelar.visible = False
        self.status_text.value = "Formulario restablecido."
        self.update()

    # Cuadro de diálogo para confirmar eliminación sin accidentes
    def _confirmar_eliminar_estudiante(self, cedula, nombre_completo):
        def ejecutar_eliminacion(e):
            self.page.dialog.open = False
            self.page.update()
            self._eliminar_estudiante(cedula)

        dlg = ft.AlertDialog(
            title=ft.Text("Confirmar Eliminación", weight=ft.FontWeight.BOLD, color="#FF1744"),
            content=ft.Text(f"¿Está seguro de que desea eliminar al estudiante {nombre_completo} (Cédula: {cedula})?\n\nEsta acción borrará sus datos, pagos asociados y archivo biométrico permanentemente.", size=13, color=TEXT_COLOR),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: setattr(self.page.dialog, 'open', False) or self.page.update()),
                ft.ElevatedButton("Sí, Eliminar", bgcolor="#FF1744", color="white", on_click=ejecutar_eliminacion)
            ]
        )
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()

    def _eliminar_estudiante(self, cedula):
        try:
            with self.db._get_connection() as conn:
                conn.execute("DELETE FROM estudiantes WHERE cedula = ?", (cedula,))
                conn.commit()
            
            ruta_foto = os.path.join(FOTOS_DIR, f"{cedula}.jpg")
            if os.path.exists(ruta_foto):
                os.remove(ruta_foto)

            self.status_text.value = f"Estudiante con cédula {cedula} eliminado."
            self.cargar_estudiantes()
            if self.editing_cedula == cedula:
                self._limpiar_formulario()
        except Exception as e:
            self.status_text.value = f"Error al eliminar: {str(e)}"
            self.update()

    def _toggle_camera(self, e):
        if not self.scanning:
            self.scanning = True
            self.video_image.visible = True
            threading.Thread(target=self._camera_loop, daemon=True).start()

    def _camera_loop(self):
        cap = cv2.VideoCapture(0)
        self.status_text.value = "Cámara activa. Posiciónate frente a ella."
        self.update()

        while self.scanning and cap.isOpened():
            ret, frame = cap.read()
            if not ret: break

            self.current_frame = frame.copy()

            _, buffer = cv2.imencode('.jpg', frame)
            self.video_image.src_base64 = base64.b64encode(buffer).decode('utf-8')
            self.update()

        cap.release()

    def _procesar_accion_principal(self, e):
        if self.editing_cedula is None:
            self._capturar_y_guardar()
        else:
            self._actualizar_estudiante_db()

    def _capturar_y_guardar(self):
        if not procesar_y_guardar_usuario:
            self.status_text.value = "Error: Módulo de procesamiento no disponible."
            self.update()
            return

        cedula = self.txt_cedula.value
        nombre = self.txt_nombre.value
        apellido = self.txt_apellido.value
        email = self.txt_email.value
        carrera = self.txt_carrera.value
        semestre_str = self.txt_semestre.value

        if not all([cedula, nombre, apellido, email, carrera]):
            self.status_text.value = "Error: Complete todos los campos."
            self.update()
            return

        if self.current_frame is None:
            self.status_text.value = "Error: Enciende la cámara primero."
            self.update()
            return

        self.scanning = False
        os.makedirs(FOTOS_DIR, exist_ok=True)
        ruta_foto = os.path.join(FOTOS_DIR, f"{cedula}.jpg")
        cv2.imwrite(ruta_foto, self.current_frame)

        try:
            semestre = int(semestre_str) if semestre_str else 1
        except ValueError:
            semestre = 1

        self.status_text.value = "Procesando IA y guardando en BD..."
        self.update()

        threading.Thread(
            target=self._guardar_thread_worker,
            args=(cedula, nombre, apellido, email, carrera, semestre),
            daemon=True
        ).start()

    def _guardar_thread_worker(self, cedula, nombre, apellido, email, carrera, semestre):
        try:
            exito, msg = procesar_y_guardar_usuario(
                cedula=cedula,
                nombre=nombre,
                apellido=apellido,
                email=email,
                carrera=carrera,
                semestre=semestre
            )
        except Exception as e:
            exito, msg = False, f"Excepción interna: {str(e)}"

        self.status_text.value = msg
        if exito:
            self.cargar_estudiantes()
            self._limpiar_formulario()

        self.update()

    def _actualizar_estudiante_db(self):
        cedula = self.editing_cedula
        nombre = self.txt_nombre.value
        apellido = self.txt_apellido.value
        email = self.txt_email.value
        carrera = self.txt_carrera.value
        semestre_str = self.txt_semestre.value

        if not all([nombre, apellido, email, carrera]):
            self.status_text.value = "Error: Complete los campos requeridos."
            self.update()
            return

        try:
            semestre = int(semestre_str) if semestre_str else 1
        except ValueError:
            semestre = 1

        if self.current_frame is not None and procesar_y_guardar_usuario:
            ruta_foto = os.path.join(FOTOS_DIR, f"{cedula}.jpg")
            cv2.imwrite(ruta_foto, self.current_frame)
            procesar_y_guardar_usuario(
                cedula=cedula, nombre=nombre, apellido=apellido,
                email=email, carrera=carrera, semestre=semestre
            )

        try:
            with self.db._get_connection() as conn:
                conn.execute(
                    "UPDATE estudiantes SET nombre = ?, apellido = ?, email = ?, carrera = ?, semestre = ?, actualizado_en = CURRENT_TIMESTAMP WHERE cedula = ?",
                    (nombre, apellido, email, carrera, semestre, cedula)
                )
                conn.commit()

            self.status_text.value = f"Estudiante {cedula} actualizado correctamente."
            self.cargar_estudiantes()
            self._limpiar_formulario()
        except Exception as e:
            self.status_text.value = f"Error al actualizar: {str(e)}"
            self.update()

    # ==========================================
    # VISTA 2: FINANZAS Y PAGOS (Con Tasa Automática)
    # ==========================================
    def vista_finanzas(self):
        txt_buscar_cedula = ft.TextField(
            label="Buscar por Cédula del Estudiante",
            prefix_icon=ft.icons.SEARCH,
            border_radius=15,
            bgcolor=BG_COLOR,
            color=TEXT_COLOR,
            label_style=ft.TextStyle(color=TEXT_COLOR),
            expand=True
        )

        periodos_options = []
        periodo_activo_id = None
        if self.db:
            try:
                with self.db._get_connection() as conn:
                    cursor = conn.execute("SELECT id, nombre, activo FROM periodos")
                    for row in cursor.fetchall():
                        p_id = row['id'] if hasattr(row, 'keys') else row[0]
                        p_nombre = row['nombre'] if hasattr(row, 'keys') else row[1]
                        p_activo = row['activo'] if hasattr(row, 'keys') else row[2]
                        periodos_options.append(ft.dropdown.Option(str(p_id), p_nombre))
                        if p_activo and not periodo_activo_id:
                            periodo_activo_id = str(p_id)
            except Exception as ex:
                print(f"Error cargando periodos: {ex}")

        dropdown_periodo_finanzas = ft.Dropdown(
            label="Periodo Académico",
            border_radius=15,
            bgcolor=BG_COLOR,
            color=TEXT_COLOR,
            label_style=ft.TextStyle(color=TEXT_COLOR),
            options=periodos_options,
            value=periodo_activo_id,
            width=220
        )

        resultado_finanzas = ft.Column(expand=True, spacing=15, scroll=ft.ScrollMode.AUTO)

        def abrir_dialogo_pago(est_id, cuota_id, monto_cuota):
            metodos_disponibles = [
                "Transferencia",
                "Pago Móvil",
                "Tarjeta de Débito"
            ]
            dd_metodo = ft.Dropdown(
                label="Método de Pago",
                value="Transferencia",
                border_radius=10,
                bgcolor=BG_COLOR,
                color=TEXT_COLOR,
                label_style=ft.TextStyle(color=TEXT_COLOR),
                focused_border_color=ACCENT_BLUE,
                options=[ft.dropdown.Option(m) for m in metodos_disponibles]
            )
            
            txt_referencia = ft.TextField(label="Referencia / Comprobante", border_radius=10, bgcolor=BG_COLOR)
            lbl_mensaje_modal = ft.Text("", size=12)

            def guardar_pago(e):
                try:
                    monto = float(monto_cuota)
                    metodo = dd_metodo.value
                    referencia = txt_referencia.value

                    with self.db._get_connection() as conn:
                        conn.execute(
                            "INSERT INTO pagos (estudiante_id, cuota_id, monto_pagado, metodo_pago, referencia) VALUES (?, ?, ?, ?, ?)",
                            (est_id, cuota_id, monto, metodo, referencia)
                        )
                        conn.commit()

                    self.page.dialog.open = False
                    self.page.update()
                    consultar_finanzas(None)
                except Exception as ex:
                    lbl_mensaje_modal.value = f"Error: {str(ex)}"
                    lbl_mensaje_modal.color = "#FF1744"
                    lbl_mensaje_modal.update()
                    
            tasa_euro = self.monitor_bcv.obtener_precio_euro()
             
            dlg = ft.AlertDialog(
                title=ft.Text("Registrar Pago de Cuota", weight=ft.FontWeight.BOLD),
                content=ft.Column(
                    tight=True, spacing=10,
                    controls=[
                        ft.Text(f"Monto a pagar: €{float(monto_cuota):.2f} (Bs{float(monto_cuota) * tasa_euro:,.2f})\n", size=14, weight=ft.FontWeight.BOLD, color=ACCENT_BLUE),
                        dd_metodo, txt_referencia, lbl_mensaje_modal
                    ]
                ),
                actions=[
                    ft.TextButton("Cancelar", on_click=lambda e: setattr(self.page.dialog, 'open', False) or self.page.update()),
                    ft.ElevatedButton("Confirmar Pago", bgcolor=ACCENT_BLUE, color="white", on_click=guardar_pago)
                ]
            )
            self.page.dialog = dlg
            dlg.open = True
            self.page.update()

        def consultar_finanzas(e):
            cedula_buscada = txt_buscar_cedula.value.strip()
            periodo_id = dropdown_periodo_finanzas.value

            resultado_finanzas.controls.clear()

            if not cedula_buscada:
                resultado_finanzas.controls.append(ft.Text("Por favor, ingrese una cédula para buscar.", color="#FF1744", weight=ft.FontWeight.BOLD))
                resultado_finanzas.update()
                return

            if not periodo_id:
                resultado_finanzas.controls.append(ft.Text("Por favor, seleccione un periodo académico.", color="#FF1744", weight=ft.FontWeight.BOLD))
                resultado_finanzas.update()
                return

            # --- OBTENER TASA DEL DÍA AUTOMÁTICA ---
            tasa_euro = self.monitor_bcv.obtener_precio_euro()

            try:
                with self.db._get_connection() as conn:
                    cursor = conn.execute("SELECT * FROM estudiantes WHERE cedula = ?", (cedula_buscada,))
                    est = cursor.fetchone()
                
                if not est:
                    resultado_finanzas.controls.append(ft.Text(f"No se encontró ningún estudiante con la cédula '{cedula_buscada}'.", color="#FF1744", weight=ft.FontWeight.BOLD))
                    resultado_finanzas.update()
                    return

                est_id = est['id'] if hasattr(est, 'keys') else est[0]
                est_nombre = f"{est['nombre']} {est['apellido']}" if hasattr(est, 'keys') else f"{est[2]} {est[3]}"

                with self.db._get_connection() as conn:
                    cursor = conn.execute(
                        "SELECT id, numero_cuota, descripcion, monto, fecha_vencimiento FROM cuotas WHERE periodo_id = ? ORDER BY numero_cuota",
                        (int(periodo_id),)
                    )
                    cuotas_periodo = cursor.fetchall()

                    cursor_pagos = conn.execute(
                        """SELECT p.cuota_id FROM pagos p 
                           JOIN cuotas c ON p.cuota_id = c.id 
                           WHERE p.estudiante_id = ? AND c.periodo_id = ?""",
                        (est_id, int(periodo_id))
                    )
                    pagos_rows = cursor_pagos.fetchall()
                    cuotas_pagadas_ids = {row['cuota_id'] if hasattr(row, 'keys') else row[0] for row in pagos_rows}

                total_cuotas = len(cuotas_periodo)
                pagadas_count = sum(1 for c in cuotas_periodo if (c['id'] if hasattr(c, 'keys') else c[0]) in cuotas_pagadas_ids)
                monto_total = sum((c['monto'] if hasattr(c, 'keys') else c[3]) for c in cuotas_periodo)
                monto_pagado = sum((c['monto'] if hasattr(c, 'keys') else c[3]) for c in cuotas_periodo if (c['id'] if hasattr(c, 'keys') else c[0]) in cuotas_pagadas_ids)
                monto_adeudado = monto_total - monto_pagado
                porcentaje = int((pagadas_count / total_cuotas * 100)) if total_cuotas > 0 else 100
                
                # Evaluación de solvencia por fecha límite
                fecha_hoy = datetime.date.today().strftime('%Y-%m-%d')
                es_solvente = True
                with self.db._get_connection() as conn:
                    c_cursor = conn.execute(
                        "SELECT id FROM cuotas WHERE periodo_id = ? AND fecha_vencimiento <= ?",
                        (int(periodo_id), fecha_hoy)
                    )
                    cuotas_vencidas = c_cursor.fetchall()
                    if cuotas_vencidas:
                        ids_vencidas = {row['id'] if hasattr(row, 'keys') else row[0] for row in cuotas_vencidas}
                        for cv_id in ids_vencidas:
                            if cv_id not in cuotas_pagadas_ids:
                                es_solvente = False
                                break

                color_estado = "#2E7D32" if es_solvente else "#FF1744"
                estado_str = "SOLVENTE" if es_solvente else "MOROSO"

                # Banner informativo con la tasa del BCV obtenida automáticamente
                banner_tasa = neu_container(
                    padding=10,
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Row([
                                ft.Icon(ft.icons.EURO, color=ACCENT_BLUE, size=18),
                                ft.Text(f"Tasa BCV del Día (EUR): Bs. {tasa_euro:,.2f}", size=13, weight=ft.FontWeight.BOLD, color=TEXT_COLOR)
                            ]),
                            ft.Text("Actualizado automáticamente vía pydolarvenezuela", size=11, color="#64748B")
                        ]
                    )
                )

                card_resumen = ft.Row(
                    spacing=15,
                    controls=[
                        neu_container(
                            expand=True, padding=15,
                            content=ft.Column([
                                ft.Text("Estudiante", size=11, color="#64748B"),
                                ft.Text(est_nombre, size=14, weight=ft.FontWeight.BOLD, color=TEXT_COLOR)
                            ])
                        ),
                        neu_container(
                            expand=True, padding=15,
                            content=ft.Column([
                                ft.Text("Estado Actual", size=11, color="#64748B"),
                                ft.Text(estado_str, size=16, weight=ft.FontWeight.BOLD, color=color_estado)
                            ])
                        ),
                        neu_container(
                            expand=True, padding=15,
                            content=ft.Column([
                                ft.Text("Monto Adeudado", size=11, color="#64748B"),
                                ft.Text(f"€ {monto_adeudado:.2f} (Bs. {monto_adeudado * tasa_euro:,.2f})", size=13, weight=ft.FontWeight.BOLD, color=TEXT_COLOR)
                            ])
                        ),
                        neu_container(
                            expand=True, padding=15,
                            content=ft.Column([
                                ft.Text("Progreso de Pago", size=11, color="#64748B"),
                                ft.Text(f"{porcentaje}%", size=16, weight=ft.FontWeight.BOLD, color=ACCENT_BLUE)
                            ])
                        )
                    ]
                )

                detalle_cuotas_col = ft.Column(spacing=8)
                detalle_cuotas_col.controls.append(
                    ft.Text("Desglose de Cuotas del Periodo Seleccionado:", size=14, weight=ft.FontWeight.BOLD, color=TEXT_COLOR)
                )

                if cuotas_periodo:
                    for cuota in cuotas_periodo:
                        c_id = cuota['id'] if hasattr(cuota, 'keys') else cuota[0]
                        c_num = cuota['numero_cuota'] if hasattr(cuota, 'keys') else cuota[1]
                        c_desc = cuota['descripcion'] if hasattr(cuota, 'keys') else cuota[2]
                        c_monto = cuota['monto'] if hasattr(cuota, 'keys') else cuota[3]
                        c_venc = cuota['fecha_vencimiento'] if hasattr(cuota, 'keys') else cuota[4]

                        monto_bs = c_monto * tasa_euro

                        pagada = c_id in cuotas_pagadas_ids
                        estado_cuota = "Pagada" if pagada else "Pendiente"
                        color_badge = "#2E7D32" if pagada else "#FF1744"

                        acciones_cuota = [
                            ft.Column(
                                spacing=0,
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                                controls=[
                                    ft.Text(f"€ {c_monto:.2f}", size=12, weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
                                    ft.Text(f"Bs. {monto_bs:,.2f}", size=10, color="#64748B")
                                ]
                            ),
                            ft.Container(
                                padding=ft.padding.symmetric(horizontal=8, vertical=2),
                                border_radius=5,
                                bgcolor=color_badge,
                                content=ft.Text(estado_cuota, size=10, color="white", weight=ft.FontWeight.BOLD)
                            )
                        ]

                        if not pagada:
                            acciones_cuota.append(
                                ft.IconButton(
                                    icon=ft.icons.PAYMENTS,
                                    icon_color=ACCENT_BLUE,
                                    icon_size=18,
                                    tooltip="Pagar cuota",
                                    on_click=lambda e, cid=c_id, monto=c_monto: abrir_dialogo_pago(est_id, cid, monto)
                                )
                            )

                        detalle_cuotas_col.controls.append(
                            ft.Container(
                                padding=10, border_radius=10, bgcolor=BG_COLOR, shadow=get_neumorphic_shadows(),
                                content=ft.Row(
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    controls=[
                                        ft.Text(f"Cuota #{c_num} - {c_desc} | Vencimiento: {c_venc}", size=12, color=TEXT_COLOR),
                                        ft.Row(spacing=12, controls=acciones_cuota, vertical_alignment=ft.CrossAxisAlignment.CENTER)
                                    ]
                                )
                            )
                        )
                else:
                    detalle_cuotas_col.controls.append(ft.Text("No hay cuotas definidas para este periodo académico.", size=12, color="#64748B"))

                resultado_finanzas.controls.extend([banner_tasa, card_resumen, ft.Divider(color="#D0D5DD"), detalle_cuotas_col])

            except Exception as ex:
                resultado_finanzas.controls.append(ft.Text(f"Error al consultar finanzas: {str(ex)}", color="#FF1744", weight=ft.FontWeight.BOLD))

            resultado_finanzas.update()

        btn_consultar = ft.ElevatedButton(
            "Consultar",
            icon=ft.icons.SEARCH,
            on_click=consultar_finanzas,
            bgcolor=ACCENT_BLUE,
            color="white",
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=15))
        )

        return ft.Column(
            expand=True, spacing=20,
            controls=[
                ft.Text("Control Financiero y Registro de Pagos", size=22, weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
                ft.Divider(color="#D0D5DD"),
                ft.Row(controls=[txt_buscar_cedula, dropdown_periodo_finanzas, btn_consultar], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, spacing=15),
                neu_container(expand=True, padding=20, content=resultado_finanzas)
            ]
        )

    # =======================================================
    # VISTA 3: GESTIÓN DE PERIODOS Y CUOTAS
    # =======================================================
    def vista_periodos_cuotas(self):
        txt_nombre_periodo = self._neu_text_field("Nombre del Periodo (Ej. 2026-II)", ft.icons.CALENDAR_TODAY)
        
        txt_fecha_inicio, row_fecha_inicio = self._crear_campo_fecha_con_picker("Fecha Inicio (AAAA-MM-DD)", ft.icons.DATE_RANGE)
        txt_fecha_fin, row_fecha_fin = self._crear_campo_fecha_con_picker("Fecha Fin (AAAA-MM-DD)", ft.icons.EVENT)
        lbl_msg_periodo = ft.Text("", size=12)

        periodos_options = []
        if self.db:
            try:
                with self.db._get_connection() as conn:
                    cursor = conn.execute("SELECT id, nombre FROM periodos")
                    for row in cursor.fetchall():
                        p_id = row['id'] if hasattr(row, 'keys') else row[0]
                        p_nombre = row['nombre'] if hasattr(row, 'keys') else row[1]
                        periodos_options.append(ft.dropdown.Option(str(p_id), p_nombre))
            except Exception as ex:
                print(f"Error cargando periodos para cuotas: {ex}")

        dropdown_periodo_cuota = ft.Dropdown(
            label="Periodo Académico Destino",
            border_radius=15, bgcolor=BG_COLOR, color=TEXT_COLOR,
            label_style=ft.TextStyle(color=TEXT_COLOR),
            options=periodos_options
        )
        
        txt_num_cuota = self._neu_text_field("Número de Cuota (Ej. 1, 2, 3)", ft.icons.NUMBERS)
        txt_descripcion_cuota = self._neu_text_field("Descripción (Ej. Cuota 1)", ft.icons.DESCRIPTION)
        txt_monto_cuota = self._neu_text_field("Monto de Cuota (€)", ft.icons.EURO)
        
        txt_vencimiento_cuota, row_vencimiento_cuota = self._crear_campo_fecha_con_picker("Fecha Vencimiento (AAAA-MM-DD)", ft.icons.TIMER)
        lbl_msg_cuota = ft.Text("", size=12)

        def registrar_periodo(e):
            nombre = txt_nombre_periodo.value
            f_ini = txt_fecha_inicio.value
            f_fin = txt_fecha_fin.value
            if not all([nombre, f_ini, f_fin]):
                lbl_msg_periodo.value = "Complete todos los campos del periodo."
                lbl_msg_periodo.color = "#FF1744"
                lbl_msg_periodo.update()
                return
            
            try:
                with self.db._get_connection() as conn:
                    conn.execute(
                        "INSERT INTO periodos (nombre, fecha_inicio, fecha_fin, activo) VALUES (?, ?, ?, 1)",
                        (nombre, f_ini, f_fin)
                    )
                    conn.commit()
                lbl_msg_periodo.value = "¡Periodo académico registrado con éxito!"
                lbl_msg_periodo.color = "#2E7D32"
                txt_nombre_periodo.value = ""
                txt_fecha_inicio.value = ""
                txt_fecha_fin.value = ""
                
                self.content_area.content = self.vista_periodos_cuotas()
                self.update()
            except Exception as ex:
                lbl_msg_periodo.value = f"Error: {str(ex)}"
                lbl_msg_periodo.color = "#FF1744"
                lbl_msg_periodo.update()

        def crear_cuota_periodo(e):
            periodo_id = dropdown_periodo_cuota.value
            num_str = txt_num_cuota.value
            descripcion = txt_descripcion_cuota.value
            monto_str = txt_monto_cuota.value
            vencimiento = txt_vencimiento_cuota.value

            if not all([periodo_id, num_str, monto_str, vencimiento]):
                lbl_msg_cuota.value = "Complete los campos obligatorios para crear la cuota."
                lbl_msg_cuota.color = "#FF1744"
                lbl_msg_cuota.update()
                return

            try:
                numero = int(num_str)
                monto = float(monto_str)
                with self.db._get_connection() as conn:
                    conn.execute(
                        "INSERT INTO cuotas (periodo_id, numero_cuota, descripcion, monto, fecha_vencimiento) VALUES (?, ?, ?, ?, ?)",
                        (int(periodo_id), numero, descripcion, monto, vencimiento)
                    )
                    conn.commit()
                lbl_msg_cuota.value = "¡Cuota asignada al periodo correctamente!"
                lbl_msg_cuota.color = "#2E7D32"
                txt_num_cuota.value = ""
                txt_descripcion_cuota.value = ""
                txt_monto_cuota.value = ""
                txt_vencimiento_cuota.value = ""
                txt_num_cuota.update()
                txt_descripcion_cuota.update()
                txt_monto_cuota.update()
                txt_vencimiento_cuota.update()
            except ValueError:
                lbl_msg_cuota.value = "Verifique que el número y el monto sean numéricos."
                lbl_msg_cuota.color = "#FF1744"
            except Exception as ex:
                lbl_msg_cuota.value = f"Error: {str(ex)}"
                lbl_msg_cuota.color = "#FF1744"
            lbl_msg_cuota.update()

        return ft.Column(
            expand=True, spacing=15,
            controls=[
                ft.Text("Configuración de Periodos y Asignación de Cuotas", size=22, weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
                ft.Divider(color="#D0D5DD"),
                ft.Row(
                    expand=True, spacing=20,
                    controls=[
                        neu_container(
                            expand=True, padding=20,
                            content=ft.Column(
                                scroll=ft.ScrollMode.AUTO,
                                spacing=15,
                                controls=[
                                    ft.Row([ft.Icon(ft.icons.DATE_RANGE, color=ACCENT_BLUE), ft.Text("Nuevo Periodo Académico", size=16, weight=ft.FontWeight.BOLD, color=TEXT_COLOR)]),
                                    txt_nombre_periodo,
                                    row_fecha_inicio,
                                    row_fecha_fin,
                                    ft.ElevatedButton("Guardar Periodo", bgcolor=ACCENT_BLUE, color="white", on_click=registrar_periodo),
                                    lbl_msg_periodo
                                ]
                            )
                        ),
                        neu_container(
                            expand=True, padding=20,
                            content=ft.Column(
                                scroll=ft.ScrollMode.AUTO,
                                spacing=15,
                                controls=[
                                    ft.Row([ft.Icon(ft.icons.PAYMENTS, color=ACCENT_BLUE), ft.Text("Definir Cuotas por Periodo", size=16, weight=ft.FontWeight.BOLD, color=TEXT_COLOR)]),
                                    dropdown_periodo_cuota,
                                    txt_num_cuota,
                                    txt_descripcion_cuota,
                                    txt_monto_cuota,
                                    row_vencimiento_cuota,
                                    ft.ElevatedButton("Crear Cuota", bgcolor=ACCENT_BLUE, color="white", on_click=crear_cuota_periodo),
                                    lbl_msg_cuota
                                ]
                            )
                        )
                    ]
                )
            ]
        )

    # ==========================================
    # VISTA 4: LOGS & ACCESOS
    # ==========================================
    def vista_logs(self):
        logs = self.db.obtener_logs_recientes(limite=50)
        logs_lv = ft.ListView(expand=True, spacing=8)
        
        for log in logs:
            nombre = f"{log.get('nombre', '')} {log.get('apellido', '')}".strip()
            # Omitir el registro si el estudiante fue eliminado (no tiene nombre o aparece como desconocido)
            if not nombre or nombre == "Desconocido" or not log.get('cedula'):
                continue
                
            reconocido = bool(log.get('reconocido', False))
            estado = "Reconocido" if reconocido else "No reconocido"
            color = "#2E7D32" if reconocido else "#FF1744"
            similitud = log.get('similitud', 0.0)
            timestamp = log.get('timestamp', '')
            
            logs_lv.controls.append(
                ft.Container(
                    padding=10, border_radius=10, bgcolor=BG_COLOR, shadow=get_neumorphic_shadows(),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(f"[{timestamp}] Estudiante: {nombre} (Cédula: {log.get('cedula', 'N/A')})", size=12, color=TEXT_COLOR),
                            ft.Text(f"{estado} ({similitud}%)", size=12, weight=ft.FontWeight.BOLD, color=color)
                        ]
                    )
                )
            )

        return ft.Column(
            expand=True, spacing=20,
            controls=[
                ft.Text("Historial de Accesos y Reconocimiento Facial", size=22, weight=ft.FontWeight.BOLD, color=TEXT_COLOR),
                ft.Divider(color="#D0D5DD"),
                neu_container(expand=True, padding=20, content=logs_lv)
            ]
        )

def main(page: ft.Page):
    page.title = "SmartFace Pro - Panel de Administración"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.bgcolor = BG_COLOR
    page.window_width = 1250
    page.window_height = 800
    
    dashboard = SmartFaceDashboard()
    page.add(dashboard)
    page.update()

if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.FLET_APP)