# vistas/historial.py
# Pantalla Historial: los ordeños de días anteriores y las alertas respondidas.
#
# La pantalla Leche muestra lo de HOY; esta muestra la evolución en el tiempo.
#
# Organización:
#   Fila 1: filtros (periodo y origen)
#   Fila 2: 4 tarjetas con el resumen del periodo
#   Fila 3: gráfica de litros por día     |  alertas de celo respondidas
#   Fila 4: tabla de ordeños (DataTable)
#
# Datos que usa (de simulador.estado()):
#   datos["registros"]  -> ordeños: ordeno, fecha, litros, kg, origen
#   datos["respuestas"] -> respuestas del ganadero: fecha, respuesta, razon

from datetime import datetime, timedelta

import flet as ft
import config
from vistas.base import VistaBase
from componentes.tarjetas import TarjetaDato
from componentes.graficas import GraficaBarras

TODOS = "todos"
DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
# Color con que se muestra cada origen en la tabla
COLOR_ORIGEN = {
    "pulsador": config.ACENTO,
    "escenario": config.MORADO,
    "ejemplo": config.TEXTO_SEC,
}


class VistaHistorial(VistaBase):

    def __init__(self):
        self._firma = None                # Para reconstruir solo si algo cambió
        self._datos = None
        self._filtrados = []              # Lo que se ve en la tabla
        super().__init__(
            titulo="Historial",
            subtitulo="Producción de leche por día y alertas de celo respondidas",
            icono=ft.Icons.TABLE_CHART,
        )

    # =============================================================
    # Construcción
    # =============================================================
    def construir(self):
        return [
            self._barra_filtros(),
            self._tarjetas_resumen(),
            ft.ResponsiveRow(spacing=16, run_spacing=16, controls=[
                self._tarjeta_grafica(), self._tarjeta_alertas(),
            ]),
            self._tarjeta_tabla(),
        ]

    def _barra_filtros(self):
        self.selector_periodo = ft.SegmentedButton(
            selected=[config.PERIODOS_HISTORIAL[0][0]],
            on_change=self._al_cambiar_filtro,
            segments=[ft.Segment(value=clave, label=texto) for clave, texto, _ in config.PERIODOS_HISTORIAL],
        )
        self.selector_origen = ft.Dropdown(
            label="Origen", value=TODOS, width=180, dense=True,
            options=[ft.DropdownOption(key=TODOS, text="Todos")] +
                    [ft.DropdownOption(key=k, text=t) for k, t in config.NOMBRE_ORIGEN.items()],
            on_select=self._al_cambiar_filtro,
        )
        # Sin hijos con expand=True: dentro de un Row(wrap=True) darían error
        return ft.Row(wrap=True, spacing=12, run_spacing=12,
                      vertical_alignment=ft.CrossAxisAlignment.CENTER,
                      controls=[self.selector_periodo, self.selector_origen])

    def _tarjetas_resumen(self):
        col = {"xs": 6, "md": 3}
        self.tarjeta_ordenos = TarjetaDato("Ordeños", ft.Icons.FORMAT_LIST_NUMBERED, "", config.AZUL, col)
        self.tarjeta_litros = TarjetaDato("Litros en total", ft.Icons.LOCAL_DRINK, "L", config.AZUL, col)
        self.tarjeta_promedio = TarjetaDato("Promedio por día", ft.Icons.EQUALIZER, "L", config.TEXTO_SEC, col)
        self.tarjeta_celos = TarjetaDato("Celos confirmados", ft.Icons.FAVORITE, "", config.ROJO, col)
        return ft.ResponsiveRow(spacing=16, run_spacing=16, controls=[
            self.tarjeta_ordenos.control, self.tarjeta_litros.control,
            self.tarjeta_promedio.control, self.tarjeta_celos.control,
        ])

    def _tarjeta_grafica(self):
        self.grafica_dias = GraficaBarras(color=config.AZUL, unidad="L")
        self.texto_grafica = ft.Text("", size=12, color=config.TEXTO_SEC)
        tarjeta = self.tarjeta(ft.Column(spacing=12, controls=[
            self.titulo_tarjeta(f"Litros por día (últimos {config.DIAS_EN_GRAFICA} días)",
                                ft.Icons.BAR_CHART, config.AZUL),
            self.grafica_dias.control,
            self.texto_grafica,
        ]))
        tarjeta.col = {"xs": 12, "lg": 8}
        return tarjeta

    def _tarjeta_alertas(self):
        self.lista_alertas = ft.Column(spacing=8)
        tarjeta = self.tarjeta(ft.Column(spacing=12, controls=[
            self.titulo_tarjeta("Alertas de celo respondidas", ft.Icons.FACT_CHECK, config.ROJO),
            self.lista_alertas,
        ]))
        tarjeta.col = {"xs": 12, "lg": 4}
        return tarjeta

    def _tarjeta_tabla(self):
        estilo_encabezado = ft.TextStyle(size=12, weight=ft.FontWeight.W_600, color=config.TEXTO_SEC)
        self.tabla = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("#")),
                ft.DataColumn(ft.Text("Fecha")),
                ft.DataColumn(ft.Text("Hora")),
                ft.DataColumn(ft.Text("Litros"), numeric=True),
                ft.DataColumn(ft.Text("Kg"), numeric=True),
                ft.DataColumn(ft.Text("Origen")),
            ],
            rows=[],
            heading_text_style=estilo_encabezado,
            data_text_style=ft.TextStyle(size=13, color=config.TEXTO),
            heading_row_color=config.PANEL_2,
            heading_row_height=40,
            data_row_min_height=40,
            data_row_max_height=44,
            column_spacing=32,
            horizontal_lines=ft.BorderSide(1, config.BORDE),
            border_radius=10,
        )
        self.texto_conteo = ft.Text("", size=12, color=config.TEXTO_SEC)
        self.texto_vacio = ft.Text("No hay ordeños con ese filtro.", color=config.TEXTO_SEC, visible=False)
        return self.tarjeta(ft.Column(spacing=12, controls=[
            self.titulo_tarjeta("Ordeños registrados", ft.Icons.TABLE_ROWS, config.AZUL),
            self.texto_conteo,
            # Scroll horizontal: en celular la tabla es más ancha que la pantalla
            ft.Row(scroll=ft.ScrollMode.AUTO, controls=[self.tabla]),
            self.texto_vacio,
        ]))

    # =============================================================
    # Eventos de los controles
    # =============================================================
    def _al_cambiar_filtro(self, e):
        self._firma = None                 # Obliga a reconstruir
        if self._datos:
            self.actualizar(self._datos)


    # =============================================================
    # Actualización periódica
    # =============================================================
    def actualizar(self, d):
        self._datos = d
        registros, respuestas = d["registros"], d["respuestas"]
        periodo = self._valor_periodo()
        origen = self.selector_origen.value or TODOS
        ultimo = registros[-1]["ordeno"] if registros else None
        # La fecha de hoy entra en la firma: a medianoche cambian los días de la gráfica
        firma = (periodo, origen, len(registros), ultimo, len(respuestas), datetime.now().date())
        if firma == self._firma:
            return                         # Nada nuevo: no se reconstruye
        self._firma = firma

        por_origen = [r for r in registros if origen == TODOS or r["origen"] == origen]
        desde = self._inicio_periodo(periodo)
        self._filtrados = [r for r in por_origen if desde is None or r["fecha"] >= desde]

        self._actualizar_resumen(self._filtrados, respuestas, desde)
        self._actualizar_grafica(por_origen)
        self._actualizar_alertas(respuestas)
        self._actualizar_tabla(self._filtrados, len(registros))

    def _valor_periodo(self):
        seleccion = self.selector_periodo.selected
        return seleccion[0] if seleccion else config.PERIODOS_HISTORIAL[0][0]

    @staticmethod
    def _inicio_periodo(periodo):
        """Fecha desde la que se cuenta el periodo (None = todo el historial).
        "7 días" incluye hoy y los 6 días anteriores completos."""
        dias = next(d for clave, _, d in config.PERIODOS_HISTORIAL if clave == periodo)
        if dias is None:
            return None
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return hoy - timedelta(days=dias - 1)

    def _actualizar_resumen(self, filtrados, respuestas, desde):
        litros = sum(r["litros"] for r in filtrados)
        dias_con_ordeno = len({r["fecha"].date() for r in filtrados})
        self.tarjeta_ordenos.actualizar(str(len(filtrados)), "En el periodo elegido")
        self.tarjeta_litros.actualizar(f"{litros:.2f}", f"{litros * config.DENSIDAD_LECHE:.1f} kg")
        if dias_con_ordeno:
            self.tarjeta_promedio.actualizar(f"{litros / dias_con_ordeno:.2f}",
                                             f"En {dias_con_ordeno} días con ordeños")
        else:
            self.tarjeta_promedio.actualizar("--", "Sin ordeños en el periodo")

        en_periodo = [r for r in respuestas if desde is None or r["fecha"] >= desde]
        confirmados = sum(1 for r in en_periodo if r["respuesta"] == "confirmar")
        falsas = len(en_periodo) - confirmados
        self.tarjeta_celos.actualizar(str(confirmados),
                                      "1 falsa alarma" if falsas == 1 else f"{falsas} falsas alarmas")

    def _actualizar_grafica(self, registros):
        """Suma los litros de cada uno de los últimos días (hoy es la última barra)."""
        hoy = datetime.now().date()
        dias = [hoy - timedelta(days=n) for n in range(config.DIAS_EN_GRAFICA - 1, -1, -1)]
        litros = {dia: 0.0 for dia in dias}
        for r in registros:
            if r["fecha"].date() in litros:
                litros[r["fecha"].date()] += r["litros"]
        etiquetas = ["Hoy" if dia == hoy else f"{DIAS_SEMANA[dia.weekday()]}\n{dia:%d/%m}" for dia in dias]
        valores = [round(litros[dia], 2) for dia in dias]
        self.grafica_dias.actualizar(etiquetas, valores, destacado=len(dias) - 1)
        con_datos = [v for v in valores if v > 0]
        if con_datos:
            self.texto_grafica.value = (f"Total {sum(valores):.1f} L · máximo {max(valores):.1f} L "
                                        f"· mínimo {min(con_datos):.1f} L (días con ordeños)")
        else:
            self.texto_grafica.value = "No hay ordeños en estos días."

    def _actualizar_alertas(self, respuestas):
        if not respuestas:
            self.lista_alertas.controls = [ft.Text(
                "Todavía no hay alertas respondidas. Cuando aparezca un posible celo, "
                "su respuesta (confirmar o falsa alarma) quedará aquí.",
                size=13, color=config.TEXTO_SEC)]
            return
        self.lista_alertas.controls = [self._fila_alerta(r) for r in reversed(respuestas[-6:])]

    def _actualizar_tabla(self, filtrados, total):
        visibles = list(reversed(filtrados))[:config.FILAS_HISTORIAL]   # Más recientes primero
        self.tabla.rows = [self._fila_tabla(r) for r in visibles]
        self.tabla.visible = bool(visibles)
        self.texto_vacio.visible = not visibles
        texto = f"{len(filtrados)} de {total} ordeños"
        if len(filtrados) > len(visibles):
            texto += f" (se muestran los {len(visibles)} más recientes)"
        self.texto_conteo.value = texto

    # =============================================================
    # Filas
    # =============================================================
    def _fila_tabla(self, r):
        color = COLOR_ORIGEN.get(r["origen"], config.TEXTO_SEC)
        origen = ft.Row(tight=True, spacing=6, controls=[
            ft.Container(width=8, height=8, border_radius=4, bgcolor=color),
            ft.Text(config.NOMBRE_ORIGEN.get(r["origen"], r["origen"]), size=13),
        ])
        return ft.DataRow(cells=[
            ft.DataCell(ft.Text(str(r["ordeno"]), color=config.AZUL, weight=ft.FontWeight.BOLD)),
            ft.DataCell(ft.Text(f"{DIAS_SEMANA[r['fecha'].weekday()]} {r['fecha']:%d/%m/%Y}")),
            ft.DataCell(ft.Text(f"{r['fecha']:%H:%M}")),
            ft.DataCell(ft.Text(f"{r['litros']:.2f}", weight=ft.FontWeight.W_600)),
            ft.DataCell(ft.Text(f"{r['kg']:.2f}", color=config.TEXTO_SEC)),
            ft.DataCell(origen),
        ])

    def _fila_alerta(self, r):
        confirmado = r["respuesta"] == "confirmar"
        color = config.ROJO if confirmado else config.TEXTO_SEC
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            border_radius=10,
            bgcolor=config.PANEL_2,
            border=ft.Border.only(left=ft.BorderSide(3, color)),
            content=ft.Row(spacing=12, controls=[
                ft.Icon(ft.Icons.FAVORITE if confirmado else ft.Icons.DO_NOT_DISTURB_ON_OUTLINED,
                        size=18, color=color),
                ft.Column(spacing=2, expand=True, controls=[
                    ft.Text("Celo confirmado" if confirmado else "Falsa alarma", size=13, color=config.TEXTO),
                    ft.Text(f"{r['fecha']:%d/%m %H:%M} · razón {r['razon']:.2f}", size=11, color=config.TEXTO_SEC),
                ]),
            ]),
        )
