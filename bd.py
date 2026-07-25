"""
bd.py - Base de datos universitaria con estudiantes y cuotas
"""

import sqlite3
import json
import numpy as np
from contextlib import contextmanager
from datetime import datetime, date
from typing import List, Dict, Optional, Union
from config import DB_PATH

class UniversityDatabase:
    """Sistema de base de datos para la universidad"""
    
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_database()
    
    @contextmanager
    def _get_connection(self):
        """Context manager para conexiones a la BD"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_database(self):
        """Inicializa la base de datos con todas las tablas"""
        with self._get_connection() as conn:
            # Tabla: ESTUDIANTES
            conn.execute("""
                CREATE TABLE IF NOT EXISTS estudiantes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cedula TEXT UNIQUE NOT NULL,
                    nombre TEXT NOT NULL,
                    apellido TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    telefono TEXT,
                    carrera TEXT NOT NULL,
                    semestre INTEGER DEFAULT 1,
                    firma_facial TEXT,  -- Embedding facial como string JSON
                    estado_financiero BOOLEAN DEFAULT 1,  -- 1=Solvente, 0=Moroso
                    activo BOOLEAN DEFAULT 1,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Tabla: ROSTROS (para múltiples registros faciales)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rostros (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    estudiante_id INTEGER NOT NULL,
                    embedding BLOB NOT NULL,
                    imagen_path TEXT,
                    metadata TEXT,
                    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE
                )
            """)
            
            # Tabla: PERIODOS ACADÉMICOS
            conn.execute("""
                CREATE TABLE IF NOT EXISTS periodos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    fecha_inicio DATE NOT NULL,
                    fecha_fin DATE NOT NULL,
                    activo BOOLEAN DEFAULT 1
                )
            """)
            
            # Tabla: CUOTAS
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cuotas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    periodo_id INTEGER NOT NULL,
                    numero_cuota INTEGER NOT NULL,
                    descripcion TEXT,
                    monto DECIMAL(10,2) NOT NULL,
                    fecha_vencimiento DATE NOT NULL,
                    FOREIGN KEY (periodo_id) REFERENCES periodos(id) ON DELETE CASCADE,
                    UNIQUE(periodo_id, numero_cuota)
                )
            """)
            
            # Tabla: PAGOS
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pagos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    estudiante_id INTEGER NOT NULL,
                    cuota_id INTEGER NOT NULL,
                    fecha_pago TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    monto_pagado DECIMAL(10,2) NOT NULL,
                    metodo_pago TEXT,
                    referencia TEXT,
                    FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE CASCADE,
                    FOREIGN KEY (cuota_id) REFERENCES cuotas(id) ON DELETE CASCADE,
                    UNIQUE(estudiante_id, cuota_id)
                )
            """)
            
            # Tabla: LOGS DE RECONOCIMIENTO
            conn.execute("""
                CREATE TABLE IF NOT EXISTS logs_reconocimiento (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    estudiante_id INTEGER,
                    similitud REAL,
                    reconocido BOOLEAN,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (estudiante_id) REFERENCES estudiantes(id) ON DELETE SET NULL
                )
            """)
            
            # Índices
            conn.execute("CREATE INDEX IF NOT EXISTS idx_estudiantes_cedula ON estudiantes(cedula)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_estudiantes_firma ON estudiantes(firma_facial)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rostros_estudiante ON rostros(estudiante_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pagos_estudiante ON pagos(estudiante_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs_reconocimiento(timestamp)")
            
            conn.commit()
    
    # ========== CRUD ESTUDIANTES ==========
    
    def registrar_estudiante(self, cedula: str, nombre: str, apellido: str, 
                            email: str, carrera: str, semestre: int = 1,
                            firma_facial: np.ndarray = None) -> int:
        """Registra un nuevo estudiante con su firma facial"""
        firma_str = None
        if firma_facial is not None:
            firma_str = json.dumps(firma_facial.tolist())
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO estudiantes 
                   (cedula, nombre, apellido, email, carrera, semestre, firma_facial) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (cedula, nombre, apellido, email, carrera, semestre, firma_str)
            )
            conn.commit()
            return cursor.lastrowid
    
    def obtener_todos_estudiantes(self):
        """Obtiene todos los estudiantes con sus campos individuales para el admin y motor"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, cedula, nombre, apellido, email, telefono, carrera, semestre, firma_facial, estado_financiero, activo 
                FROM estudiantes 
                WHERE activo = 1
            """)
            rows = cursor.fetchall()
            
            estudiantes = []
            for row in rows:
                firma = None
                if row['firma_facial']:
                    try:
                        firma = np.array(json.loads(row['firma_facial']))
                    except:
                        firma = None
                
                estudiantes.append({
                    "id": row['id'],
                    "cedula": row['cedula'],
                    "nombre": row['nombre'],
                    "apellido": row['apellido'],
                    "email": row['email'],
                    "telefono": row['telefono'],
                    "carrera": row['carrera'],
                    "semestre": row['semestre'],
                    "firma": firma,
                    "estado_financiero": row['estado_financiero'],
                    "es_activo": bool(row['activo'])
                })
            return estudiantes
    
    def actualizar_estado_financiero(self, estudiante_id: int):
        """Actualiza automáticamente el estado financiero del estudiante"""
        with self._get_connection() as conn:
            estado = conn.execute("""
                SELECT 
                    CASE 
                        WHEN COUNT(p.id) = COUNT(c.id) THEN 1
                        ELSE 0
                    END as solvente
                FROM cuotas c
                LEFT JOIN pagos p ON p.cuota_id = c.id AND p.estudiante_id = ?
                WHERE c.periodo_id = (SELECT id FROM periodos WHERE activo = 1 LIMIT 1)
            """, (estudiante_id,)).fetchone()
            
            if estado:
                conn.execute(
                    "UPDATE estudiantes SET estado_financiero = ? WHERE id = ?",
                    (estado[0], estudiante_id)
                )
                conn.commit()
                return bool(estado[0])
        return False
    
    # ========== GESTIÓN DE PERIODOS Y CUOTAS ==========
    
    def crear_periodo(self, nombre: str, fecha_inicio: str, fecha_fin: str) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO periodos (nombre, fecha_inicio, fecha_fin) VALUES (?, ?, ?)",
                (nombre, fecha_inicio, fecha_fin)
            )
            conn.commit()
            return cursor.lastrowid
    
    def crear_cuota(self, periodo_id: int, numero: int, monto: float, 
                    fecha_vencimiento: str, descripcion: str = None) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO cuotas 
                   (periodo_id, numero_cuota, descripcion, monto, fecha_vencimiento) 
                   VALUES (?, ?, ?, ?, ?)""",
                (periodo_id, numero, descripcion, monto, fecha_vencimiento)
            )
            conn.commit()
            return cursor.lastrowid
    
    def registrar_pago(self, estudiante_id: int, cuota_id: int, 
                       monto: float, metodo: str = None, referencia: str = None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO pagos (estudiante_id, cuota_id, monto_pagado, metodo_pago, referencia) 
                   VALUES (?, ?, ?, ?, ?)""",
                (estudiante_id, cuota_id, monto, metodo, referencia)
            )
            conn.commit()
            self.actualizar_estado_financiero(estudiante_id)
            return cursor.lastrowid
    
    # ========== OBTENER ESTADO FINANCIERO ==========
    
    def obtener_estado_financiero(self, estudiante_id: int) -> Dict:
        """Obtiene el estado financiero completo de un estudiante"""
        with self._get_connection() as conn:
            estudiante = conn.execute(
                "SELECT * FROM estudiantes WHERE id = ?", (estudiante_id,)
            ).fetchone()
            
            if not estudiante:
                return None
            
            periodo = conn.execute(
                "SELECT * FROM periodos WHERE activo = 1 LIMIT 1"
            ).fetchone()
            
            if not periodo:
                return {
                    'estudiante': dict(estudiante),
                    'error': 'No hay periodo activo'
                }
            
            cuotas = conn.execute("""
                SELECT 
                    c.*,
                    p.id as pago_id,
                    p.fecha_pago,
                    p.monto_pagado,
                    p.metodo_pago,
                    CASE WHEN p.id IS NOT NULL THEN 1 ELSE 0 END as pagada
                FROM cuotas c
                LEFT JOIN pagos p ON p.cuota_id = c.id AND p.estudiante_id = ?
                WHERE c.periodo_id = ?
                ORDER BY c.numero_cuota
            """, (estudiante_id, periodo['id'])).fetchall()
            
            total_cuotas = len(cuotas)
            cuotas_pagadas = sum(1 for c in cuotas if c['pagada'])
            cuotas_pendientes = total_cuotas - cuotas_pagadas
            
            monto_total = sum(c['monto'] for c in cuotas)
            monto_pagado = sum(c['monto_pagado'] or 0 for c in cuotas if c['pagada'])
            monto_adeudado = monto_total - monto_pagado
            
            estado = 'SOLVENTE' if cuotas_pendientes == 0 else 'MOROSO'
            
            return {
                'estudiante': dict(estudiante),
                'periodo': dict(periodo),
                'resumen': {
                    'total_cuotas': total_cuotas,
                    'cuotas_pagadas': cuotas_pagadas,
                    'cuotas_pendientes': cuotas_pendientes,
                    'monto_total': float(monto_total),
                    'monto_pagado': float(monto_pagado),
                    'monto_adeudado': float(monto_adeudado),
                    'estado_financiero': estado,
                    'porcentaje': round((monto_pagado / monto_total * 100), 1) if monto_total > 0 else 0
                },
                'detalle_cuotas': [dict(c) for c in cuotas]
            }
    
    # ========== LOGS ==========
    
    def registrar_log(self, estudiante_id: int, similitud: float, reconocido: bool):
        # Generamos la hora local exacta del sistema operativo
        timestamp_local = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO logs_reconocimiento (estudiante_id, similitud, reconocido, timestamp) VALUES (?, ?, ?, ?)",
                (estudiante_id, similitud, reconocido, timestamp_local)
            )
            conn.commit()
    
    def obtener_logs_recientes(self, limite: int = 100):
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT l.*, e.nombre, e.apellido, e.cedula
                FROM logs_reconocimiento l
                JOIN estudiantes e ON l.estudiante_id = e.id
                ORDER BY l.timestamp DESC
                LIMIT ?
            """, (limite,)).fetchall()
            return [dict(row) for row in rows]