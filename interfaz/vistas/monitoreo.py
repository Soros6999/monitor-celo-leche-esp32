# vistas/monitoreo.py
# Pantalla de Monitoreo.

import flet as ft
import config
from vistas.base import VistaBase


class VistaMonitoreo(VistaBase):

    def __init__(self):
        super().__init__(
            titulo="Monitoreo",
            subtitulo="Estado de la vaca y de la leche en tiempo real",
            icono=ft.Icons.MONITOR_HEART,
        )

    def construir(self):
        # Contenido provisional: se reemplaza en los siguientes commits
        return [
            self.tarjeta(
                ft.Text(
                    "Aquí irán: semáforo de estado, tarjetas con actividad, línea base y razón,\ngráfica en tiempo real y nivel del balde.",
                    color=config.TEXTO_SEC,
                )
            )
        ]
