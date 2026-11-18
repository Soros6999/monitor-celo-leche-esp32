# vistas/control.py
# Pantalla de Control.

import flet as ft
import config
from vistas.base import VistaBase


class VistaControl(VistaBase):

    def __init__(self):
        super().__init__(
            titulo="Control",
            subtitulo="Comandos para la ESP32 y controles de simulación",
            icono=ft.Icons.TUNE,
        )

    def construir(self):
        # Contenido provisional: se reemplaza en los siguientes commits
        return [
            self.tarjeta(
                ft.Text(
                    "Aquí irán: umbral de celo, intervalo de envío, tara, calibración,\nsilenciar buzzer y los controles para simular la vaca y la balanza.",
                    color=config.TEXTO_SEC,
                )
            )
        ]
