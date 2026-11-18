# componentes/graficas.py
# Gráficas de línea basadas en flet_charts.
#
# GraficaLineas recibe varias series (nombre, color) y se actualiza con
# listas de valores: cada lista se convierte en puntos (x = posición, y = valor).

import flet as ft
import flet_charts as fch
import config


class GraficaLineas:

    def __init__(self, series, alto=230, max_y=None, decimales=2, puntos_visibles=False, curvas=True,
                 rango_minimo=None):
        """series: lista de tuplas (nombre, color, punteada).

        rango_minimo: si se indica, el eje Y no arranca en 0 sino que se ajusta
        a los datos con al menos ese rango (sirve para ver variaciones pequeñas,
        como el ruido de la balanza).
        """
        self.series = series
        self.max_y_fijo = max_y
        self.rango_minimo = rango_minimo
        self.decimales = decimales
        self._ultimos_datos = None     # Para no redibujar si nada cambió

        self.datos = [
            fch.LineChartData(
                points=[],
                color=color,
                stroke_width=3 if not punteada else 2,
                curved=curvas and not punteada,
                prevent_curve_over_shooting=True,
                dash_pattern=[6, 5] if punteada else None,
                point=puntos_visibles and not punteada,
                below_line_bgcolor=ft.Colors.with_opacity(0.12, color) if i == 0 else None,
            )
            for i, (nombre, color, punteada) in enumerate(series)
        ]
        self.grafica = fch.LineChart(
            data_series=self.datos,
            height=alto,
            min_y=0,
            interactive=True,
            horizontal_grid_lines=fch.ChartGridLines(color=config.BORDE, width=1, dash_pattern=[3, 3]),
            left_axis=fch.ChartAxis(label_size=44, label_spacing=0.05),
            bottom_axis=fch.ChartAxis(show_labels=False),
            border=ft.Border.all(1, config.BORDE),
            animation=ft.Animation(0, ft.AnimationCurve.LINEAR),
        )
        self.leyenda = ft.Row(
            spacing=16, wrap=True,
            controls=[self._item_leyenda(nombre, color, punteada) for nombre, color, punteada in series],
        )
        self.control = ft.Column(spacing=10, controls=[self.grafica, self.leyenda])

    @staticmethod
    def _item_leyenda(nombre, color, punteada):
        return ft.Row(tight=True, spacing=6, controls=[
            ft.Container(width=18, height=3 if not punteada else 2, bgcolor=color, border_radius=2),
            ft.Text(nombre, size=12, color=config.TEXTO_SEC),
        ])

    def actualizar(self, listas):
        """listas: una lista de valores por cada serie, en el mismo orden.

        Si los datos son iguales a los de la última vez, no hace nada:
        redibujar una gráfica sin cambios solo hace más lenta la interfaz.
        """
        if listas == self._ultimos_datos:
            return
        self._ultimos_datos = [list(v) for v in listas]
        maximo, minimo = 0.0, None
        for datos, valores in zip(self.datos, listas):
            datos.points = [fch.LineChartDataPoint(x=i, y=v) for i, v in enumerate(valores)]
            if valores:
                maximo = max(maximo, max(valores))
                minimo = min(valores) if minimo is None else min(minimo, min(valores))
        largo = max((len(v) for v in listas), default=1)
        self.grafica.min_x = 0
        self.grafica.max_x = max(largo - 1, 1)

        if self.rango_minimo is not None and minimo is not None:
            # Eje ajustado a los datos, centrado en su promedio
            centro = (maximo + minimo) / 2
            mitad = max((maximo - minimo) * 0.6, self.rango_minimo / 2)
            piso, tope = centro - mitad, centro + mitad
        else:
            piso = 0
            tope = self.max_y_fijo or (maximo * 1.15 if maximo > 0 else 0.1)
        self.grafica.min_y = piso
        self.grafica.max_y = tope
        # Etiquetas del eje Y: piso, mitad y tope
        self.grafica.left_axis.labels = [
            fch.ChartAxisLabel(value=v, label=ft.Text(f"{v:.{self.decimales}f}", size=10, color=config.TEXTO_SEC))
            for v in (piso, (piso + tope) / 2, tope)
        ]
