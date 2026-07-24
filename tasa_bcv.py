import json
import urllib.request

class MonitorBCV:
    """
    Clase personalizada para obtener la tasa oficial del Euro en el BCV
    sin depender de librerías externas ni sufrir errores de versiones.
    """
    def __init__(self):
        # Endpoints públicos y gratuitos que proveen la tasa BCV en tiempo real
        self.endpoints = [
            "https://ve.dolarapi.com/v1/euros/oficial",
            "https://pydolarvenezuela-api.vercel.app/api/v1/euro/unit/bcv"
        ]

    def obtener_precio_euro(self) -> float:
        """
        Consulta la tasa oficial del Euro y retorna el valor en Bolívares.
        Si falla la conexión, intenta con un servidor de respaldo.
        """
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

        for url in self.endpoints:
            try:
                req = urllib.request.Request(url, headers=headers)
                # Timeout de 5 segundos para no congelar la app si no hay internet
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        data = json.loads(response.read().decode('utf-8'))
                        
                        # Formato 1: API DolarApi (monto en campo "promedio")
                        if "promedio" in data and data["promedio"] is not None:
                            return float(data["promedio"])
                        
                        # Formato 2: API PyDolarVenezuela (monto en campo "price")
                        elif "price" in data and data["price"] is not None:
                            return float(data["price"])
                            
            except Exception as e:
                print(f"[MonitorBCV] No se pudo obtener tasa desde {url}: {e}")
                continue

        # Valor predeterminado si no hay conexión a internet
        return 0.0