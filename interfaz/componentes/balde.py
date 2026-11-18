# componentes/balde.py
# Dibujo del balde de leche: el nivel sube y baja según los kilos medidos.
# Se arma con un Stack: el contorno del balde y, encima, un rectángulo
# cuya altura es proporcional al peso.

import flet as ft
import config


class IndicadorBalde:

    ALTO = 150
    ANCHO = 110

    def __init__(self, capacidad_kg):
        self.capacidad = capacidad_kg
        self.leche = ft.Container(
            width=self.ANCHO, height=0,
            bgcolor=ft.Colors.with_opacity(0.85, config.AZUL),
            border_radius=ft.BorderRadius.only(bottom_left=14, bottom_right=14),
            animate=ft.Animation(400, ft.AnimationCurve.EASE_OUT),
        )
        self.texto_nivel = ft.Text("0 %", size=12, color=config.TEXTO, weight=ft.FontWeight.BOLD)
        self.control = ft.Stack(
            width=self.ANCHO, height=self.ALTO,
            controls=[
                ft.Container(  # Contorno
                    width=self.ANCHO, height=self.ALTO,
                    border=ft.Border.all(2, config.BORDE),
                    border_radius=ft.BorderRadius.only(bottom_left=16, bottom_right=16, top_left=4, top_right=4),
                    bgcolor=config.FONDO,
                ),
                ft.Container(content=self.leche, bottom=2, left=0),
                ft.Container(content=self.texto_nivel, top=8, left=0, width=self.ANCHO,
                             alignment=ft.Alignment.CENTER),
            ],
        )

    def actualizar(self, kg):
        fraccion = max(0.0, min(kg / self.capacidad, 1.0))
        self.leche.height = (self.ALTO - 4) * fraccion
        self.texto_nivel.value = f"{fraccion * 100:.0f} %"
