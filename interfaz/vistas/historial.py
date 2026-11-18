# vistas/historial.py
# Pantalla de Historial.

import flet as ft
import config
from vistas.base import VistaBase


class VistaHistorial(VistaBase):

    def __init__(self):
        super().__init__(
            titulo="Historial",
            subtitulo="Registro de ordeños",
            icono=ft.Icons.TABLE_CHART,
        )

    def construir(self):
        # Contenido provisional: se reemplaza en los siguientes commits
        return [
            self.tarjeta(
                ft.Text(
                    "Aquí irán: tabla de ordeños, gráfica de litros y exportación a CSV.",
                    color=config.TEXTO_SEC,
                )
            )
        ]
