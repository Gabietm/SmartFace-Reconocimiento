import flet as ft
import cv2
import subprocess
import sys
import app
import admin
from smartface_engine import SmartFaceEngine

def main(page: ft.Page):
    page.title = "Sistema de Acceso - Instituto Politécnico Santiago Mariño"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.window_width = 450
    page.window_height = 700
    page.window_resizable = False
    
    engine = SmartFaceEngine()

    # Datos simulados del Administrador (Preguntas de Seguridad y Clave)
    admin_data = {
        "nombre": "admin",
        "edad": "30",
        "cedula": "12345678",
        "email": "admin@smartface.com",
        "codigo_postal": "6201",
        "familiar": "maria",
        "password": "admin"
    }

    # Campos de recuperación de contraseña
    rec_inputs = {
        "nombre": ft.TextField(label="Nombre", width=350),
        "edad": ft.TextField(label="Edad", width=350),
        "cedula": ft.TextField(label="Cédula", width=350),
        "email": ft.TextField(label="Email", width=350),
        "codigo_postal": ft.TextField(label="Código Postal", width=350),
        "familiar": ft.TextField(label="Familiar Cercano", width=350),
    }

    new_pass_input = ft.TextField(label="Nueva Contraseña", password=True, can_reveal_password=True, width=350)
    confirm_pass_input = ft.TextField(label="Confirmar Contraseña", password=True, can_reveal_password=True, width=350)
    admin_pass_input = ft.TextField(label="Contraseña de Administrador", password=True, can_reveal_password=True, width=350)

    # Contenedor dinámico principal para las vistas
    content_area = ft.Column(alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # Funciones de Navegación usando Subprocess para abrir app.py o admin.py independientemente
    def cambiar_a_app(e=None):
        page.window_destroy()
        try:
            subprocess.Popen([sys.executable, "app.py"])
        except Exception as ex:
            print(f"Error al abrir app.py: {ex}")

    def cambiar_a_admin(e=None):
        page.window_destroy()
        try:
            subprocess.Popen([sys.executable, "admin.py"])
        except Exception as ex:
            print(f"Error al abrir admin.py: {ex}")

    # Autenticación Biométrica para Administrador
    def login_biometrico(e):
        cap = cv2.VideoCapture(0)
        page.snack_bar = ft.SnackBar(ft.Text("Escaneando rostro del administrador..."))
        page.snack_bar.open = True
        page.update()
        
        authenticated = False
        for _ in range(30):
            ret, frame = cap.read()
            if not ret:
                break
            
            results = engine.reconocer(frame) if hasattr(engine, 'reconocer') else []
            if results:
                authenticated = True
                break
            
            cv2.imshow("Verificacion Facial - Presione Q para salir", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

        if authenticated:
            page.snack_bar = ft.SnackBar(ft.Text("¡Rostro reconocido con éxito!"))
            page.snack_bar.open = True
            page.update()
            cambiar_a_admin()
        else:
            page.snack_bar = ft.SnackBar(ft.Text("Rostro no reconocido. Intente de nuevo."))
            page.snack_bar.open = True
            page.update()

    def validar_admin_pass(e):
        if admin_pass_input.value == admin_data["password"]:
            cambiar_a_admin()
        else:
            page.snack_bar = ft.SnackBar(ft.Text("Contraseña de administrador incorrecta"))
            page.snack_bar.open = True
            page.update()

    def verificar_preguntas(e):
        acierto = True
        for key, field in rec_inputs.items():
            if field.value.strip().lower() != admin_data[key].lower():
                acierto = False
                break
        
        if acierto:
            mostrar_vista_cambio_password()
        else:
            page.snack_bar = ft.SnackBar(ft.Text("Datos incorrectos. Verifique sus respuestas."))
            page.snack_bar.open = True
            page.update()

    def guardar_nueva_password(e):
        if not new_pass_input.value or not confirm_pass_input.value:
            page.snack_bar = ft.SnackBar(ft.Text("Complete ambos campos."))
            page.snack_bar.open = True
            page.update()
            return

        if new_pass_input.value == confirm_pass_input.value:
            admin_data["password"] = new_pass_input.value
            page.snack_bar = ft.SnackBar(ft.Text("Contraseña actualizada con éxito."))
            page.snack_bar.open = True
            page.update()
            mostrar_vista_admin()
        else:
            page.snack_bar = ft.SnackBar(ft.Text("Las contraseñas no coinciden."))
            page.snack_bar.open = True
            page.update()

    # --- DEFINICIÓN DE VISTAS ---

    def mostrar_vista_usuario(e=None):
        content_area.controls.clear()
        content_area.controls.extend([
            ft.Text("Acceso para Usuarios", size=16, weight=ft.FontWeight.BOLD),
            ft.Container(height=20),
            ft.ElevatedButton("Acceder al Sistema", color=ft.colors.WHITE, bgcolor=ft.colors.BLUE, on_click=cambiar_a_app)
        ])
        page.update()

    def mostrar_vista_admin(e=None):
        admin_pass_input.value = ""
        content_area.controls.clear()
        content_area.controls.extend([
            ft.Text("Panel de Administrador", size=16, weight=ft.FontWeight.BOLD),
            ft.Container(height=10),
            admin_pass_input,
            ft.Container(height=10),
            ft.ElevatedButton("Iniciar Sesión", color=ft.colors.WHITE, bgcolor=ft.colors.GREEN, on_click=validar_admin_pass),
            ft.TextButton("¿Olvidó su contraseña?", on_click=lambda _: mostrar_vista_recuperacion()),
            ft.Divider(),
            ft.ElevatedButton("📷 Acceso Biométrico Facial", color=ft.colors.WHITE, bgcolor=ft.colors.PURPLE, on_click=login_biometrico)
        ])
        page.update()

    def mostrar_vista_recuperacion(e=None):
        content_area.controls.clear()
        controls_list = [
            ft.Text("Preguntas de Seguridad", size=16, weight=ft.FontWeight.BOLD),
            ft.Container(height=10)
        ]
        for field in rec_inputs.values():
            field.value = ""
            controls_list.append(field)
            controls_list.append(ft.Container(height=5))
        
        controls_list.append(ft.ElevatedButton("Validar Respuestas", color=ft.colors.WHITE, bgcolor=ft.colors.ORANGE, on_click=verificar_preguntas))
        controls_list.append(ft.TextButton("Volver al Login", on_click=mostrar_vista_admin))
        
        content_area.controls.extend(controls_list)
        page.update()

    def mostrar_vista_cambio_password():
        new_pass_input.value = ""
        confirm_pass_input.value = ""
        content_area.controls.clear()
        content_area.controls.extend([
            ft.Text("Establecer Nueva Contraseña", size=16, weight=ft.FontWeight.BOLD),
            ft.Container(height=10),
            new_pass_input,
            ft.Container(height=5),
            confirm_pass_input,
            ft.Container(height=15),
            ft.ElevatedButton("Guardar Contraseña", color=ft.colors.WHITE, bgcolor=ft.colors.GREEN, on_click=guardar_nueva_password)
        ])
        page.update()

    # Selector de Rol (Dropdown principal)
    rol_dropdown = ft.Dropdown(
        label="Seleccione Rol",
        value="Usuario",
        options=[
            ft.dropdown.Option("Usuario"),
            ft.dropdown.Option("Administrador")
        ],
        on_change=lambda e: mostrar_vista_usuario() if e.control.value == "Usuario" else mostrar_vista_admin(),
        width=350
    )

    # Layout Principal de la Ventana de Login con el título requerido
    page.add(
        ft.Column([
            # Título Institucional
            ft.Container(
                content=ft.Column([
                    ft.Text("Bienvenido al", size=15, color=ft.colors.GREY_700),
                    ft.Text("Instituto Politécnico", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_900),
                    ft.Text("Santiago Mariño", size=18, weight=ft.FontWeight.BOLD, color=ft.colors.BLUE_900),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.only(bottom=15)
            ),
            rol_dropdown,
            ft.Container(height=10),
            content_area
        ], 
        alignment=ft.MainAxisAlignment.START, 
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
    )

    # Inicializar por defecto en la vista Usuario
    mostrar_vista_usuario()

if __name__ == "__main__":
    ft.app(target=main)