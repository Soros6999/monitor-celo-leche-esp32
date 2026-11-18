# componentes/escenario.py
# Muestra el avance del escenario de demostración.
#
#   - LineaTiempoEscenario: las 4 fases en fila, marcando la actual y las terminadas.
#   - FranjaEscenario: franja compacta que aparece arriba en todas las pantallas
#     mientras el escenario está corriendo.

import flet as ft
import config


class LineaTiempoEscenario:

    def __init__(self):
        self.cajas = []
        for i, (nombre, _, duracion, _) in enumerate(config.ESCENARIO):
            icono = ft.Icon(ft.Icons.RADIO_BUTTON_UNCHECKED, size=16, color=config.TEXTO_SEC)
            caja = ft.Container(
                col={"xs": 6, "md": 3},     # 2 x 2 en el celular, 4 en fila en el computador
                padding=10,
                border_radius=10,
                bgcolor=config.PANEL_2,
                border=ft.Border.all(1, config.BORDE),
                content=ft.Column(spacing=4, controls=[
                    ft.Row(spacing=6, controls=[icono, ft.Text(f"Fase {i + 1}", size=11, color=config.TEXTO_SEC)]),
                    ft.Text(nombre, size=13, weight=ft.FontWeight.W_600, color=config.TEXTO),
                    ft.Text(f"{duracion} s", size=11, color=config.TEXTO_SEC),
                ]),
            )
            self.cajas.append((caja, icono))
        self.barra = ft.ProgressBar(value=0, color=config.ACENTO, bgcolor=config.PANEL_2,
                                    bar_height=6, border_radius=3)
        self.texto = ft.Text("", size=13, color=config.TEXTO)
        self.control = ft.Column(spacing=10, controls=[
            ft.ResponsiveRow(spacing=8, run_spacing=8, controls=[caja for caja, _ in self.cajas]),
            self.barra,
            self.texto,
        ])

    def actualizar(self, info):
        if info is None:
            return
        for i, (caja, icono) in enumerate(self.cajas):
            if i < info["fase"]:          # Terminada
                caja.border = ft.Border.all(1, config.BORDE)
                icono.icon, icono.color = ft.Icons.CHECK_CIRCLE, config.VERDE
            elif i == info["fase"]:       # Actual
                caja.border = ft.Border.all(2, config.ACENTO)
                icono.icon, icono.color = ft.Icons.PLAY_CIRCLE, config.ACENTO
            else:                         # Pendiente
                caja.border = ft.Border.all(1, config.BORDE)
                icono.icon, icono.color = ft.Icons.RADIO_BUTTON_UNCHECKED, config.TEXTO_SEC
        self.barra.value = info["progreso"]
        self.texto.value = f"{info['descripcion']}. Faltan {info['restante']:.0f} s para la siguiente fase."


class FranjaEscenario:

    def __init__(self):
        self.texto = ft.Text("", size=13, color=config.TEXTO, expand=True)
        self.barra = ft.ProgressBar(value=0, color=config.ACENTO, bgcolor=config.PANEL_2,
                                    bar_height=4, border_radius=2)
        self.control = ft.Container(
            visible=False,
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            border_radius=12,
            bgcolor=config.PANEL,
            border=ft.Border.all(1, config.ACENTO),
            content=ft.Column(spacing=8, controls=[
                ft.Row(spacing=10, controls=[
                    ft.Icon(ft.Icons.SMART_DISPLAY, color=config.ACENTO, size=20),
                    self.texto,
                ]),
                self.barra,
            ]),
        )

    def actualizar(self, info):
        self.control.visible = info is not None
        if info is None:
            return
        self.texto.value = (f"Escenario de demostración · Fase {info['fase'] + 1} de {info['total_fases']}: "
                            f"{info['nombre']} · faltan {info['restante']:.0f} s")
        self.barra.value = info["progreso"]
