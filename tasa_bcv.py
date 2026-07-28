import json
import os
import urllib.request
from datetime import datetime

class MonitorBCV:
    def __init__(self, cache_file="tasa_cache.json"):
        self.cache_file = cache_file
        self.endpoints = [
            "https://ve.dolarapi.com/v1/euros/oficial",
            "https://pydolarvenezuela-api.vercel.app/api/v1/euro/unit/bcv"
        ]

    def obtener_precio_euro(self) -> float:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

        for url in self.endpoints:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode('utf-8'))
                        
                        precio = 0.0
                        if "promedio" in data and data["promedio"]:
                            precio = float(data["promedio"])
                        elif "venta" in data and data["venta"]:
                            precio = float(data["venta"])
                        elif "price" in data and data["price"]:
                            precio = float(data["price"])
                            
                        # Si encontramos un precio válido, lo guardamos en caché y lo devolvemos
                        if precio > 0:
                            try:
                                with open(self.cache_file, "w") as f:
                                    json.dump({"precio": precio}, f)
                            except Exception:
                                pass
                            return precio
                            
            except Exception as e:
                print(f"[MonitorBCV] Error al conectar con {url}: {e}")
                continue

        # Si falla la conexión a internet con todos los endpoints, leemos la última tasa guardada
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r") as f:
                    data = json.load(f)
                    cached_precio = float(data.get("precio", 0.0))
                    if cached_precio > 0:
                        print("[MonitorBCV] Sin conexión: Usando tasa en caché local.")
                        return cached_precio
            except Exception as e:
                print(f"[MonitorBCV] Error al leer la caché local: {e}")

        return 0.0