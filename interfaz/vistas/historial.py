# vistas/historial.py
# Pantalla Historial: los ordeños de días anteriores.
#
# La pantalla Leche muestra lo de HOY; esta muestra la evolución en el tiempo.
#
# Organización:
#   Fila 1: filtros (periodo y origen)
#   Fila 2: tabla de ordeños (DataTable)
#
# Datos que usa (de simulador.estado()):
#   datos["registros"]  -> ordeños: ordeno, fecha, litros, kg, origen

from datetime import datetime, timedelta

import flet as ft
import config
from vistas.base import VistaBase

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
            subtitulo="Ordeños registrados, con filtro por periodo y origen",
            icono=ft.Icons.TABLE_CHART,
        )

    # =============================================================
    # Construcción
    # =============================================================
    def construir(self):
        return [
            self._barra_filtros(),
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
        registros = d["registros"]
        periodo = self._valor_periodo()
        origen = self.selector_origen.value or TODOS
        ultimo = registros[-1]["ordeno"] if registros else None
        # La fecha de hoy entra en la firma: a medianoche cambia el periodo
        firma = (periodo, origen, len(registros), ultimo, datetime.now().date())
        if firma == self._firma:
            return                         # Nada nuevo: no se reconstruye
        self._firma = firma

        por_origen = [r for r in registros if origen == TODOS or r["origen"] == origen]
        desde = self._inicio_periodo(periodo)
        self._filtrados = [r for r in por_origen if desde is None or r["fecha"] >= desde]

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

