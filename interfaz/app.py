# app.py
# Clase principal de la aplicación: configura la ventana, crea el simulador
# y las pantallas, maneja la navegación y ejecuta la actualización periódica.
#
# Diseño adaptable:
#   - Pantalla ancha (computador): menú lateral (NavigationRail).
#   - Pantalla angosta (celular):  barra inferior (NavigationBar).

import asyncio
import traceback

import flet as ft
import config
from modelo.simulador import SimuladorSistema
from componentes.barra_estado import BarraEstado
from componentes.alarma import BannerAlarma
from componentes.escenario import FranjaEscenario
from vistas.vaca import VistaVaca
from vistas.leche import VistaLeche
from vistas.control import VistaControl
from vistas.historial import VistaHistorial
from vistas.eventos import VistaEventos


class AplicacionMonitor:

    # Secciones del menú: (texto, ícono normal, ícono seleccionado)
    SECCIONES = [
        ("Vaca", ft.Icons.SENSORS_OUTLINED, ft.Icons.SENSORS),
        ("Leche", ft.Icons.WATER_DROP_OUTLINED, ft.Icons.WATER_DROP),
        ("Historial", ft.Icons.TABLE_CHART_OUTLINED, ft.Icons.TABLE_CHART),
        ("Eventos", ft.Icons.NOTIFICATIONS_OUTLINED, ft.Icons.NOTIFICATIONS),
        ("Control", ft.Icons.TUNE_OUTLINED, ft.Icons.TUNE),
    ]

    def __init__(self, page: ft.Page):
        self.page = page
        self.indice = 0          # Sección seleccionada
        self.modo_movil = None   # Se decide según el ancho de la ventana
        self.alarma_anterior = False

        self._configurar_ventana()

        # Fuente de datos: hoy el simulador; en la integración, el cliente MQTT
        self.simulador = SimuladorSistema()

        # Una instancia de cada pantalla (todas heredan de VistaBase)
        # (en el mismo orden que SECCIONES)
        self.vistas = [
            VistaVaca(),
            VistaLeche(),
            VistaHistorial(notificar=self.notificar),
            VistaEventos(),
            VistaControl(self.simulador, al_cambiar=self._refrescar, notificar=self.notificar),
        ]

        # Partes comunes a todas las pantallas
        self.barra_estado = BarraEstado(
            al_ver_origen=self._mostrar_origen_datos,
            al_cambiar_conexion=self._alternar_conexion,
        )
        self.banner_alarma = BannerAlarma(al_silenciar=self._silenciar_buzzer)
        self.franja_escenario = FranjaEscenario()
        self.contenedor_vista = ft.Container(expand=True, content=self.vistas[self.indice].control)
        self.area_principal = ft.Container(
            expand=True,
            padding=24,
            content=ft.Column(
                expand=True, spacing=16,
                controls=[self.barra_estado.control, self.banner_alarma.control,
                          self.franja_escenario.control, self.contenedor_vista],
            ),
        )

        self.menu_lateral = self._crear_menu_lateral()
        self.barra_inferior = self._crear_barra_inferior()

        # Evento: cuando cambia el tamaño de la ventana, se reorganiza
        self.page.on_resize = self._al_cambiar_tamano
        self._organizar()

        # Primera actualización y arranque del ciclo periódico
        self._refrescar()
        self.page.run_task(self._ciclo_actualizacion)

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

    # ---------- Actualización periódica ----------
    async def _ciclo_actualizacion(self):
        """Cada PERIODO_ACTUALIZACION_S segundos: avanza la simulación y
        refresca la pantalla. Es el equivalente al after() de Tkinter."""
        while True:
            await asyncio.sleep(config.PERIODO_ACTUALIZACION_S)
            try:
                self.simulador.avanzar(config.PERIODO_ACTUALIZACION_S)
                self._refrescar()
            except Exception:
                # Un error en una actualización no debe detener la aplicación
                traceback.print_exc()

    def _refrescar(self):
        datos = self.simulador.estado()
        self.barra_estado.actualizar(datos)
        self.banner_alarma.actualizar(datos)
        self.franja_escenario.actualizar(datos["escenario"])
        # Polimorfismo: cada vista sabe cómo actualizarse con los mismos datos
        self.vistas[self.indice].actualizar(datos)
        self._revisar_alarma_nueva(datos)
        self.page.update()

    def _revisar_alarma_nueva(self, datos):
        """Muestra una ventana emergente solo cuando EMPIEZA un posible celo."""
        if datos["alarma"] and not self.alarma_anterior:
            self._mostrar_dialogo_celo(datos)
        self.alarma_anterior = datos["alarma"]

    def _mostrar_dialogo_celo(self, datos):
        dialogo = ft.AlertDialog(
            modal=True,
            icon=ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color=config.ROJO, size=40),
            title=ft.Text("Posible celo detectado"),
            content=ft.Container(width=460, content=ft.Column(tight=True, spacing=12, controls=[
                ft.Text(f"La vaca 01 se mueve {datos['razon']:.1f} veces más de lo normal "
                        f"(umbral {datos['umbral_celo']:.2f})."),
                ft.Text("Es una alerta, no un diagnóstico. Después de observar al animal, "
                        "registre lo que encontró.", color=config.TEXTO_SEC),
            ])),
            actions=[
                ft.TextButton("Silenciar y revisar luego", on_click=self._silenciar_desde_dialogo),
                ft.OutlinedButton(content="Falsa alarma", on_click=lambda e: self._responder_alerta("falsa")),
                ft.FilledButton(content="Confirmar celo", icon=ft.Icons.CHECK,
                                on_click=lambda e: self._responder_alerta("confirmar")),
            ],
        )
        self.page.show_dialog(dialogo)

    def _responder_alerta(self, respuesta):
        """El ganadero confirma o descarta la alerta: queda en los eventos."""
        self.page.pop_dialog()
        self.simulador.responder_alerta(respuesta)
        self.notificar("Celo confirmado y registrado" if respuesta == "confirmar"
                       else "Registrado como falsa alarma")
        self._refrescar()

    # ---------- Acciones de la barra superior (eventos on_click) ----------
    def _mostrar_origen_datos(self, e):
        self.page.show_dialog(ft.AlertDialog(
            icon=ft.Icon(ft.Icons.SCIENCE, color=config.MORADO, size=36),
            title=ft.Text("Datos simulados"),
            content=ft.Text(
                "En este parcial la interfaz no está conectada a la ESP32.\n\n"
                "Los datos los genera SimuladorSistema, que aplica la misma lógica del "
                "firmware (línea base, razón, estabilidad de la balanza) y produce los "
                "mismos mensajes JSON en los mismos tópicos MQTT.\n\n"
                "En la integración final se reemplaza el simulador por un cliente MQTT "
                "real, sin cambiar las pantallas."
            ),
            actions=[ft.Button(content="Entendido", on_click=lambda ev: self.page.pop_dialog())],
        ))

    def _alternar_conexion(self, e):
        conectado = not self.simulador.conectado
        self.simulador.cambiar_conexion(conectado)
        self.notificar("Conexión restablecida" if conectado else
                       "Conexión perdida: los datos se siguen midiendo pero no se envían", conectado)
        self._refrescar()

    # ---------- Acciones comunes ----------
    def _silenciar_buzzer(self, e=None):
        ok, texto = self.simulador.ejecutar_comando(config.TOPICO_CMD_BUZZER, "silenciar")
        self.notificar(texto, ok)
        self._refrescar()

    def _silenciar_desde_dialogo(self, e):
        self.page.pop_dialog()
        self._silenciar_buzzer()

    def notificar(self, texto, ok=True):
        """Mensaje breve en la parte inferior (SnackBar)."""
        self.page.show_dialog(ft.SnackBar(
            content=ft.Text(texto, color="#FFFFFF"),
            bgcolor=config.VERDE if ok else config.ROJO,
            duration=3000,
        ))

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
        self.contenedor_vista.content = self.vistas[self.indice].control
        self._refrescar()   # La pantalla nueva aparece ya con datos

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
