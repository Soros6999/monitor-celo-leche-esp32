# componentes/semaforo.py
# Semáforo visual: los mismos tres LEDs del circuito (verde, amarillo, rojo).
# Solo el LED del estado actual queda encendido y con brillo (sombra de color).

import flet as ft
import config


class SemaforoVisual:

    # Estado que enciende cada LED, en orden
    LEDS = [
        (config.ESTADO_NORMAL, config.VERDE),
        (config.ESTADO_ALTA, config.AMARILLO),
        (config.ESTADO_CELO, config.ROJO),
    ]

    def __init__(self, tamano=34):
        self.estado_actual = None
        self.luces = {}
        for estado, color in self.LEDS:
            self.luces[estado] = ft.Container(
                width=tamano, height=tamano,
                border_radius=tamano / 2,
                bgcolor=config.PANEL_2,
                border=ft.Border.all(2, color),
                animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
            )
        self.control = ft.Container(
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            border_radius=30,
            bgcolor=config.FONDO,
            content=ft.Row(spacing=12, tight=True, controls=list(self.luces.values())),
        )

    def mostrar(self, estado):
        """Enciende solo el LED que corresponde al estado."""
        if estado == self.estado_actual:
            return                      # Sin cambios: no se redibuja
        self.estado_actual = estado
        for nombre, color in self.LEDS:
            luz = self.luces[nombre]
            encendido = (nombre == estado)
            luz.bgcolor = color if encendido else config.PANEL_2
            luz.shadow = ft.BoxShadow(blur_radius=18, spread_radius=1, color=color) if encendido else None
