import sqlite3
import os

if not os.path.exists('base_de_datos'):
    os.makedirs('base_de_datos')

conexion = sqlite3.connect('base_de_datos/control_acceso.db')
cursor = conexion.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        cedula TEXT PRIMARY KEY,
        nombres TEXT,
        apellidos TEXT,
        carrera_especialidad TEXT,
        estado_financiero INTEGER,
        firma_facial TEXT
    )
''')

conexion.commit()
conexion.close()
print("Base de datos actualizada: tabla 'usuarios' recreada con estado booleano (INTEGER).")