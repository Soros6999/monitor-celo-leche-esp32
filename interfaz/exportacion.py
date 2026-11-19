# exportacion.py
# Exporta los ordeños a un archivo CSV que se puede abrir en Excel.
#
# Está separado de la vista (igual que validacion.py) para que:
#   - se pueda probar sin abrir la interfaz,
#   - la vista solo decida CUÁNDO exportar, no CÓMO se escribe el archivo.

import csv
import os
from datetime import datetime

import config

ENCABEZADOS = ["Ordeño", "Fecha", "Hora", "Litros", "Kg", "Origen"]


def _numero(valor):
    """2 decimales con el separador decimal de config (coma para Excel en español)."""
    return f"{valor:.2f}".replace(".", config.DECIMAL_CSV)


def exportar_csv(registros, carpeta=None):
    """Escribe los registros en un CSV nuevo y devuelve la ruta del archivo.

    El nombre lleva fecha y hora (historial_20261118_153000.csv) para no
    sobrescribir exportaciones anteriores. Si no se puede escribir (permisos,
    disco lleno), lanza OSError: la vista lo atrapa y avisa al usuario.
    """
    if carpeta is None:
        # Ruta relativa a ESTE archivo, no a la carpeta desde donde se ejecutó
        carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), config.CARPETA_EXPORTES)
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, f"historial_{datetime.now():%Y%m%d_%H%M%S}.csv")

    # utf-8-sig agrega una marca al inicio para que Excel muestre bien la ñ y las tildes
    with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.writer(archivo, delimiter=config.SEPARADOR_CSV)
        escritor.writerow(ENCABEZADOS)
        for r in registros:
            escritor.writerow([
                r["ordeno"],
                f"{r['fecha']:%Y-%m-%d}",
                f"{r['fecha']:%H:%M:%S}",
                _numero(r["litros"]),
                _numero(r["kg"]),
                config.NOMBRE_ORIGEN.get(r["origen"], r["origen"]),
            ])
    return ruta
