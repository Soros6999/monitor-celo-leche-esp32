# vistas/eventos.py
# Pantalla Eventos: todo lo que pasó en el sistema, con fecha y hora.
#
#   - Pestaña "Eventos": alertas, respuestas del ganadero, comandos, ordeños,
#     conexión y sistema. Se puede filtrar por tipo (lista desplegable) y
#     buscar por texto (campo que filtra mientras se escribe).
#   - Pestaña "Mensajes MQTT": los mensajes que publica la ESP32, con su
#     tópico y su JSON. Es la "vista técnica" de la comunicación.

import flet as ft
import config
from vistas.base import VistaBase

# Ícono y color de cada tipo de evento
ESTILO_EVENTO = {
    config.EVENTO_ALERTA: (ft.Icons.WARNING_AMBER_ROUNDED, config.ROJO),
    config.EVENTO_COMANDO: (ft.Icons.SETTINGS_REMOTE, config.ACENTO),
    config.EVENTO_ORDENO: (ft.Icons.WATER_DROP, config.AZUL),
    config.EVENTO_CONEXION: (ft.Icons.WIFI, config.MORADO),
    config.EVENTO_SISTEMA: (ft.Icons.INFO_OUTLINE, config.TEXTO_SEC),
}
TODOS = "Todos"
# Filtro de la pestaña MQTT: (clave, texto, parte del tópico que se busca)
GRUPOS_TOPICO = [
    (TODOS, "Todos", ""),
    ("celo", "Collar (celo)", "/celo/"),
    ("peso", "Peso en vivo", "/leche/balanza/peso"),
    ("registro", "Ordeños", "/leche/balanza/registro"),
    ("sistema", "Sistema", "/sistema/"),
]
MAXIMO_FILAS = 100        # Filas que se dibujan como máximo (las más recientes)


class VistaEventos(VistaBase):

    def __init__(self):
        self._firma = None            # Para reconstruir la lista solo si algo cambió
        self._datos = None
        super().__init__(
            titulo="Eventos",
            subtitulo="Alertas, comandos, ordeños y comunicación, con fecha y hora",
            icono=ft.Icons.NOTIFICATIONS,
        )

    # =============================================================
    # Construcción
    # =============================================================
    def construir(self):
        self.selector_pestana = ft.SegmentedButton(
            selected=["eventos"],
            on_change=self._al_cambiar_filtro,
            segments=[
                ft.Segment(value="eventos", label="Eventos", icon=ft.Icons.LIST_ALT),
                ft.Segment(value="mqtt", label="Mensajes MQTT", icon=ft.Icons.WIFI_TETHERING),
            ],
        )
        self.selector_tipo = ft.Dropdown(
            label="Tipo", value=TODOS, width=200, dense=True,
            options=[ft.DropdownOption(key=TODOS, text=TODOS)] +
                    [ft.DropdownOption(key=t, text=t) for t in config.TIPOS_EVENTO],
            on_select=self._al_cambiar_filtro,
        )
        self.selector_topico = ft.Dropdown(
            label="Tópico", value=TODOS, width=200, dense=True, visible=False,
            options=[ft.DropdownOption(key=clave, text=texto) for clave, texto, _ in GRUPOS_TOPICO],
            on_select=self._al_cambiar_filtro,
        )
        self.campo_buscar = ft.TextField(
            label="Buscar", prefix_icon=ft.Icons.SEARCH, width=260, dense=True,
            on_change=self._al_cambiar_filtro,          # Filtra mientras se escribe
        )
        self.texto_conteo = ft.Text("", size=12, color=config.TEXTO_SEC)
        self.filtros = ft.Row(wrap=True, spacing=12, run_spacing=12,
                              vertical_alignment=ft.CrossAxisAlignment.CENTER,
                              controls=[self.selector_tipo, self.selector_topico,
                                        self.campo_buscar, self.texto_conteo])

        self.resumen = ft.Row(wrap=True, spacing=8, run_spacing=8)
        self.lista = ft.Column(spacing=8)
        return [
            self.selector_pestana,
            self.tarjeta(ft.Column(spacing=16, controls=[
                self.filtros,
                self.resumen,
                ft.Divider(height=1, color=config.BORDE),
                self.lista,
            ])),
        ]

    # =============================================================
    # Eventos de los controles
    # =============================================================
    def _al_cambiar_filtro(self, e):
        self._firma = None                 # Obliga a reconstruir la lista
        if self._datos:
            self.actualizar(self._datos)

    # =============================================================
    # Actualización periódica
    # =============================================================
    def actualizar(self, d):
        self._datos = d
        pestana = self.selector_pestana.selected[0] if self.selector_pestana.selected else "eventos"
        es_mqtt = pestana == "mqtt"
        self.selector_tipo.visible = not es_mqtt
        self.selector_topico.visible = es_mqtt
        texto = (self.campo_buscar.value or "").strip().lower()

        if es_mqtt:
            elementos = d["mensajes"]
            ultimo = elementos[-1]["fecha"] if elementos else None
        else:
            elementos = d["eventos"]
            ultimo = elementos[-1].fecha if elementos else None
        firma = (pestana, self.selector_tipo.value, self.selector_topico.value, texto, len(elementos), ultimo)
        if firma == self._firma:
            return                         # Nada nuevo: no se reconstruye
        self._firma = firma

        if es_mqtt:
            self._mostrar_mqtt(elementos, texto)
        else:
            self._mostrar_eventos(elementos, texto)

    def _mostrar_eventos(self, eventos, texto):
        tipo = self.selector_tipo.value or TODOS
        filtrados = [ev for ev in eventos
                     if (tipo == TODOS or ev.tipo == tipo) and (not texto or texto in ev.mensaje.lower())]

        # Resumen: cuántos eventos hay de cada tipo
        self.resumen.controls = [self._chip_conteo(t, sum(1 for ev in eventos if ev.tipo == t))
                                 for t in config.TIPOS_EVENTO]
        self.resumen.visible = True
        self.texto_conteo.value = f"{len(filtrados)} de {len(eventos)} eventos"

        if not filtrados:
            self.lista.controls = [ft.Text("No hay eventos con ese filtro.", color=config.TEXTO_SEC)]
            return
        self.lista.controls = [self._fila_evento(ev) for ev in reversed(filtrados[-MAXIMO_FILAS:])]

    def _mostrar_mqtt(self, mensajes, texto):
        clave = self.selector_topico.value or TODOS
        parte = next((p for c, _, p in GRUPOS_TOPICO if c == clave), "")
        filtrados = [m for m in mensajes
                     if parte in m["topico"]
                     and (not texto or texto in m["topico"].lower() or texto in m["carga"].lower())]
        self.resumen.visible = False
        self.texto_conteo.value = f"{len(filtrados)} de {len(mensajes)} mensajes publicados por la ESP32 (simulada)"
        if not filtrados:
            self.lista.controls = [ft.Text("No hay mensajes con ese filtro.", color=config.TEXTO_SEC)]
            return
        self.lista.controls = [self._fila_mensaje(m) for m in reversed(filtrados[-MAXIMO_FILAS:])]

    # =============================================================
    # Filas
    # =============================================================
    def _chip_conteo(self, tipo, cantidad):
        icono, color = ESTILO_EVENTO[tipo]
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=10, vertical=5),
            border_radius=20, bgcolor=config.PANEL_2,
            content=ft.Row(tight=True, spacing=6, controls=[
                ft.Icon(icono, size=14, color=color),
                ft.Text(f"{tipo}: {cantidad}", size=12, color=config.TEXTO),
            ]),
        )

    def _fila_evento(self, ev):
        icono, color = ESTILO_EVENTO.get(ev.tipo, (ft.Icons.CIRCLE, config.TEXTO_SEC))
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            border_radius=10,
            bgcolor=config.PANEL_2,
            border=ft.Border.only(left=ft.BorderSide(3, color)),
            content=ft.Row(spacing=12, controls=[
                ft.Icon(icono, size=20, color=color),
                ft.Column(spacing=2, expand=True, controls=[
                    ft.Text(ev.mensaje, size=13, color=config.TEXTO),
                    ft.Text(f"{ev.fecha:%d/%m/%Y %H:%M:%S} · {ev.tipo}", size=11, color=config.TEXTO_SEC),
                ]),
            ]),
        )

    def _fila_mensaje(self, m):
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            border_radius=10,
            bgcolor=config.PANEL_2,
            border=ft.Border.only(left=ft.BorderSide(3, config.MORADO)),
            content=ft.Column(spacing=4, controls=[
                ft.Row(spacing=8, controls=[
                    ft.Icon(ft.Icons.NORTH_EAST, size=14, color=config.MORADO),
                    ft.Text(m["topico"], size=12, color=config.MORADO, expand=True, selectable=True),
                    ft.Text(f"{m['fecha']:%H:%M:%S}", size=11, color=config.TEXTO_SEC),
                ]),
                ft.Text(m["carga"], size=13, color=config.TEXTO, font_family="monospace", selectable=True),
            ]),
        )
