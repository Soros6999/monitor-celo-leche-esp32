# vistas/eventos.py
# Pantalla de Eventos.

import flet as ft
import config
from vistas.base import VistaBase


class VistaEventos(VistaBase):

    def __init__(self):
        super().__init__(
            titulo="Eventos",
            subtitulo="Alertas, comandos y cambios de conexión",
            icono=ft.Icons.NOTIFICATIONS,
        )

    def construir(self):
        # Contenido provisional: se reemplaza en los siguientes commits
        return [
            self.tarjeta(
                ft.Text(
                    "Aquí irá: la lista de eventos con fecha y hora, con filtro por tipo.",
                    color=config.TEXTO_SEC,
                )
            )
        ]
