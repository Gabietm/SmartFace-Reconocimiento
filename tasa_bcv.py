import json
import urllib.request
from datetime import datetime

class MonitorBCV:
    def __init__(self):
        self.endpoints = [
            "https://ve.dolarapi.com/v1/euros/oficial",
            "https://pydolarvenezuela-api.vercel.app/api/v1/euro/unit/bcv"
        ]

    def obtener_precio_euro(self) -> float:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        hoy_str = datetime.now().strftime("%Y-%m-%d") # Fecha actual del sistema

        for url in self.endpoints:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode('utf-8'))
                        
                        # Opcional: Validar si la API incluye fecha de actualización y chequear si es vieja
                        # fecha_api = data.get("fechaActualizacion", "")
                        # if fecha_api and not fecha_api.startswith(hoy_str):
                        #     print(f"[Aviso] La tasa de {url} corresponde a una fecha anterior ({fecha_api})")
                        
                        if "promedio" in data and data["promedio"]:
                            return float(data["promedio"])
                        elif "venta" in data and data["venta"]:
                            return float(data["venta"])
                        elif "price" in data and data["price"]:
                            return float(data["price"])
                            
            except Exception as e:
                print(f"[MonitorBCV] Error al conectar con {url}: {e}")
                continue

        return 0.0