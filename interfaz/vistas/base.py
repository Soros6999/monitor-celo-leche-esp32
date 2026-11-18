# vistas/base.py
# Clase base de todas las pantallas.
#
# Cada pantalla (Monitoreo, Control, Historial, Eventos) HEREDA de VistaBase:
#   - VistaBase arma lo que todas tienen en común: el encabezado con título,
#     subtítulo e ícono, y una columna con desplazamiento.
#   - Cada subclase sobrescribe construir() para agregar su propio contenido
#     y actualizar() para refrescar sus datos (polimorfismo).

import flet as ft
import config


class VistaBase:

    def __init__(self, titulo, subtitulo, icono):
        self.titulo = titulo
        self.subtitulo = subtitulo
        self.icono = icono

        # Columna principal de la pantalla: encabezado + contenido propio
        self.control = ft.Column(
            expand=True,
            spacing=20,
            scroll=ft.ScrollMode.AUTO,
            controls=[self._crear_encabezado()],
        )
        self.control.controls.extend(self.construir())

    def _crear_encabezado(self):
        """Título y subtítulo comunes a todas las pantallas."""
        return ft.Row(
            spacing=14,
            controls=[
                ft.Container(
                    width=48, height=48, border_radius=12,
                    bgcolor=config.PANEL_2,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(self.icono, color=config.ACENTO, size=26),
                ),
                ft.Column(
                    spacing=2,
                    expand=True,     # Ocupa el resto del ancho: el subtítulo puede saltar de línea
                    controls=[
                        ft.Text(self.titulo, size=26, weight=ft.FontWeight.BOLD,
                                color=config.TEXTO),
                        ft.Text(self.subtitulo, size=13, color=config.TEXTO_SEC),
                    ],
                ),
            ],
        )

    def construir(self):
        """Devuelve la lista de controles propios de la pantalla.

        Las subclases DEBEN sobrescribir este método.
        """
        return []

    def actualizar(self, datos):
        """Refresca la pantalla con datos nuevos del sistema.

        Por defecto no hace nada; cada subclase decide qué mostrar.
        """
        pass

    @staticmethod
    def titulo_tarjeta(texto, icono, color=config.ACENTO):
        """Ícono + título que encabeza cada tarjeta."""
        return ft.Row(spacing=8, controls=[
            ft.Icon(icono, size=18, color=color),
            ft.Text(texto, size=15, weight=ft.FontWeight.W_600, color=config.TEXTO, expand=True),
        ])

    @staticmethod
    def tarjeta(contenido, expand=False, padding=20):
        """Panel con fondo y bordes redondeados (equivale a un Frame)."""
        return ft.Container(
            expand=expand,
            padding=padding,
            border_radius=16,
            bgcolor=config.PANEL,
            border=ft.Border.all(1, config.BORDE),
            content=contenido,
        )
