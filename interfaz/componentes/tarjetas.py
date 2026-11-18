# componentes/tarjetas.py
# TarjetaDato: muestra una variable con su título, ícono, valor y unidad.
# Se usa para actividad, línea base, razón, umbral, kilos, litros, etc.

import flet as ft
import config


class TarjetaDato:

    def __init__(self, titulo, icono, unidad="", color=config.ACENTO, col=None):
        self.texto_valor = ft.Text("--", size=28, weight=ft.FontWeight.BOLD, color=config.TEXTO)
        self.texto_unidad = ft.Text(unidad, size=13, color=config.TEXTO_SEC)
        self.texto_detalle = ft.Text("", size=12, color=config.TEXTO_SEC)
        self.icono = ft.Icon(icono, color=color, size=20)

        self.control = ft.Container(
            col=col,
            padding=16,
            border_radius=14,
            bgcolor=config.PANEL,
            border=ft.Border.all(1, config.BORDE),
            content=ft.Column(
                spacing=6,
                controls=[
                    ft.Row(spacing=8, controls=[
                        self.icono,
                        ft.Text(titulo, size=13, color=config.TEXTO_SEC),
                    ]),
                    ft.Row(
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.END,
                        controls=[self.texto_valor, self.texto_unidad],
                    ),
                    self.texto_detalle,
                ],
            ),
        )

    def actualizar(self, valor, detalle=None, color=None):
        self.texto_valor.value = valor
        self.texto_valor.color = color or config.TEXTO
        if detalle is not None:
            self.texto_detalle.value = detalle


class Chip:
    """Etiqueta pequeña con punto o ícono de color: Conectado, Estable, Simulado...

    Si recibe al_hacer_clic, se vuelve un botón: muestra un borde y reacciona
    al clic (evento on_click, equivalente al command de Tkinter).
    """

    def __init__(self, texto, color=config.TEXTO_SEC, icono=None, al_hacer_clic=None, ayuda=None):
        self.punto = ft.Container(width=8, height=8, border_radius=4, bgcolor=color)
        self.icono = ft.Icon(icono, size=14, color=color) if icono else None
        self.texto = ft.Text(texto, size=12, color=config.TEXTO)
        controles = [self.icono or self.punto, self.texto]
        if al_hacer_clic:
            controles.append(ft.Icon(ft.Icons.TOUCH_APP, size=12, color=config.TEXTO_SEC))
        self.control = ft.Container(
            padding=ft.Padding.symmetric(horizontal=10, vertical=5),
            border_radius=20,
            bgcolor=config.PANEL_2,
            border=ft.Border.all(1, config.BORDE) if al_hacer_clic else None,
            on_click=al_hacer_clic,
            ink=al_hacer_clic is not None,
            tooltip=ayuda,
            content=ft.Row(tight=True, spacing=6, controls=controles),
        )

    def actualizar(self, texto, color):
        self.texto.value = texto
        if self.icono:
            self.icono.color = color
        else:
            self.punto.bgcolor = color
