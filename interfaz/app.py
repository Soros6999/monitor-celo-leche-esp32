# app.py
# Clase principal de la aplicación: configura la ventana, crea las pantallas
# y maneja la navegación entre ellas.
#
# Diseño adaptable:
#   - Pantalla ancha (computador): menú lateral (NavigationRail).
#   - Pantalla angosta (celular):  barra inferior (NavigationBar).

import flet as ft
import config
from vistas.monitoreo import VistaMonitoreo
from vistas.control import VistaControl
from vistas.historial import VistaHistorial
from vistas.eventos import VistaEventos


class AplicacionMonitor:

    # Secciones del menú: (texto, ícono normal, ícono seleccionado)
    SECCIONES = [
        ("Monitoreo", ft.Icons.MONITOR_HEART_OUTLINED, ft.Icons.MONITOR_HEART),
        ("Control", ft.Icons.TUNE_OUTLINED, ft.Icons.TUNE),
        ("Historial", ft.Icons.TABLE_CHART_OUTLINED, ft.Icons.TABLE_CHART),
        ("Eventos", ft.Icons.NOTIFICATIONS_OUTLINED, ft.Icons.NOTIFICATIONS),
    ]

    def __init__(self, page: ft.Page):
        self.page = page
        self.indice = 0          # Sección seleccionada
        self.modo_movil = None   # Se decide según el ancho de la ventana

        self._configurar_ventana()

        # Una instancia de cada pantalla (todas heredan de VistaBase)
        self.vistas = [
            VistaMonitoreo(),
            VistaControl(),
            VistaHistorial(),
            VistaEventos(),
        ]

        # Área donde se muestra la pantalla seleccionada
        self.area_principal = ft.Container(
            expand=True,
            padding=24,
            content=self.vistas[self.indice].control,
        )

        self.menu_lateral = self._crear_menu_lateral()
        self.barra_inferior = self._crear_barra_inferior()

        # Evento: cuando cambia el tamaño de la ventana, se reorganiza
        self.page.on_resize = self._al_cambiar_tamano
        self._organizar()

    # ---------- Configuración ----------
    def _configurar_ventana(self):
        self.page.title = config.TITULO_APP
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = config.FONDO
        self.page.padding = 0
        self.page.theme = ft.Theme(color_scheme_seed=config.ACENTO)
        self.page.dark_theme = ft.Theme(color_scheme_seed=config.ACENTO)
        # Tamaño de la ventana (solo aplica en escritorio)
        self.page.window.width = config.ANCHO_VENTANA
        self.page.window.height = config.ALTO_VENTANA
        self.page.window.min_width = config.ANCHO_MINIMO
        self.page.window.min_height = config.ALTO_MINIMO

    # ---------- Navegación ----------
    def _crear_menu_lateral(self):
        marca = ft.Container(
            padding=ft.Padding.only(top=8, bottom=16),
            content=ft.Column(
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
                controls=[
                    ft.Icon(ft.Icons.AGRICULTURE, color=config.ACENTO, size=40),
                    ft.Text(config.TITULO_APP, size=14, weight=ft.FontWeight.BOLD,
                            color=config.TEXTO, text_align=ft.TextAlign.CENTER),
                    ft.Text(config.SUBTITULO_APP, size=11, color=config.TEXTO_SEC),
                ],
            ),
        )
        return ft.NavigationRail(
            selected_index=self.indice,
            extended=True,
            min_extended_width=220,
            bgcolor=config.PANEL,
            indicator_color=config.PANEL_2,
            leading=marca,
            on_change=self._al_cambiar_seccion,
            destinations=[
                ft.NavigationRailDestination(icon=icono, selected_icon=icono_sel, label=texto)
                for texto, icono, icono_sel in self.SECCIONES
            ],
        )

    def _crear_barra_inferior(self):
        return ft.NavigationBar(
            selected_index=self.indice,
            bgcolor=config.PANEL,
            indicator_color=config.PANEL_2,
            on_change=self._al_cambiar_seccion,
            destinations=[
                ft.NavigationBarDestination(icon=icono, selected_icon=icono_sel, label=texto)
                for texto, icono, icono_sel in self.SECCIONES
            ],
        )

    def _al_cambiar_seccion(self, e):
        """Evento on_change del menú: muestra la pantalla elegida."""
        self.indice = e.control.selected_index
        # Mantener sincronizados los dos menús
        self.menu_lateral.selected_index = self.indice
        self.barra_inferior.selected_index = self.indice
        self.area_principal.content = self.vistas[self.indice].control
        self.page.update()

    # ---------- Diseño adaptable ----------
    def _al_cambiar_tamano(self, e):
        self._organizar()

    def _organizar(self):
        """Elige menú lateral o barra inferior según el ancho disponible."""
        ancho = self.page.width or config.ANCHO_VENTANA
        movil = ancho < config.ANCHO_MODO_MOVIL
        if movil == self.modo_movil:
            return                       # No cambió nada
        self.modo_movil = movil

        self.page.controls.clear()
        if movil:
            self.area_principal.padding = 14
            self.page.navigation_bar = self.barra_inferior
            self.page.add(self.area_principal)
        else:
            self.area_principal.padding = 24
            self.page.navigation_bar = None
            self.page.add(
                ft.Row(
                    expand=True,
                    spacing=0,
                    controls=[self.menu_lateral, self.area_principal],
                )
            )
        self.page.update()
