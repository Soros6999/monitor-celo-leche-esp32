# componentes/medidor.py
# Medidor de la razón (actividad ÷ línea base) con las tres zonas de color.
#
#   0 ─── verde ─── 1.5 ── amarillo ── 2.0 ───── rojo ───── 4
#                          ▲ razón actual
#
# El ancho de cada zona es proporcional a su rango (expand), así el medidor
# se adapta a cualquier ancho de pantalla. Si se cambia el umbral de celo,
# las zonas se recalculan.

import flet as ft
import config

ESCALA_MAXIMA = 4.0      # La razón se dibuja hasta 4 (más allá queda al final)
UNIDADES = 100           # Resolución de los "expand" (centésimas de razón)


class MedidorRazon:

    def __init__(self):
        self.zona_verde = ft.Container(height=14, bgcolor=config.VERDE,
                                       border_radius=ft.BorderRadius.only(top_left=7, bottom_left=7))
        self.zona_amarilla = ft.Container(height=14, bgcolor=config.AMARILLO)
        self.zona_roja = ft.Container(height=14, bgcolor=config.ROJO,
                                      border_radius=ft.BorderRadius.only(top_right=7, bottom_right=7))

        self.relleno_izq = ft.Container(height=1)
        self.relleno_der = ft.Container(height=1)
        self.texto_marcador = ft.Text("", size=12, weight=ft.FontWeight.BOLD, color=config.TEXTO)
        self.marcador = ft.Column(
            spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[self.texto_marcador, ft.Icon(ft.Icons.ARROW_DROP_DOWN, color=config.TEXTO, size=22)],
        )

        self.etiqueta_alta = ft.Text("", size=11, color=config.TEXTO_SEC)
        self.etiqueta_celo = ft.Text("", size=11, color=config.TEXTO_SEC)
        self.etiquetas = ft.Row(spacing=0, controls=[
            ft.Container(content=ft.Text("0", size=11, color=config.TEXTO_SEC)),
            self.etiqueta_alta, self.etiqueta_celo,
            ft.Container(content=ft.Text(f"{ESCALA_MAXIMA:g}+", size=11, color=config.TEXTO_SEC)),
        ])

        self.control = ft.Column(spacing=2, controls=[
            ft.Row(spacing=0, controls=[self.relleno_izq, self.marcador, self.relleno_der]),
            ft.Row(spacing=0, controls=[self.zona_verde, self.zona_amarilla, self.zona_roja]),
            self.etiquetas,
        ])
        self._ultimo = None

    def actualizar(self, razon, umbral_alta, umbral_celo, visible=True):
        clave = (round(razon, 2), umbral_alta, umbral_celo, visible)
        if clave == self._ultimo:
            return                          # Nada cambió: no se redibuja
        self._ultimo = clave

        # Zonas proporcionales a su rango
        self.zona_verde.expand = int(umbral_alta * UNIDADES)
        self.zona_amarilla.expand = int((umbral_celo - umbral_alta) * UNIDADES)
        self.zona_roja.expand = int((ESCALA_MAXIMA - umbral_celo) * UNIDADES)

        # Etiquetas de los umbrales bajo el borde de cada zona
        self.etiqueta_alta.value = f"{umbral_alta:g}"
        self.etiqueta_celo.value = f"{umbral_celo:g}"
        self.etiquetas.controls[0].expand = int(umbral_alta * UNIDADES)
        self.etiquetas.controls[1].expand = int((umbral_celo - umbral_alta) * UNIDADES)
        self.etiquetas.controls[2].expand = int((ESCALA_MAXIMA - umbral_celo) * UNIDADES)

        # Posición del marcador
        self.marcador.visible = visible
        posicion = max(0.0, min(razon, ESCALA_MAXIMA))
        self.relleno_izq.expand = max(int(posicion * UNIDADES), 1)
        self.relleno_der.expand = max(int((ESCALA_MAXIMA - posicion) * UNIDADES), 1)
        self.texto_marcador.value = f"{razon:.2f}"
