# vistas/leche.py
# Pantalla Leche: la estación de ordeño (celda de carga + HX711).
# Muestra la medición en vivo, por qué el peso se considera estable o no,
# y el resumen de los ordeños de hoy. El historial de días anteriores está
# en la pantalla Historial.
#
# Organización:
#   Fila 1: balde en vivo              |  gráfica de estabilidad
#   Fila 2: 4 tarjetas con el resumen de hoy
#   Fila 3: lista de ordeños de hoy

from datetime import datetime, timedelta

import flet as ft
import config
from vistas.base import VistaBase
from componentes.tarjetas import TarjetaDato, Chip
from componentes.graficas import GraficaLineas
from componentes.balde import IndicadorBalde


class VistaLeche(VistaBase):

    def __init__(self):
        self._ordenos_mostrados = None
        super().__init__(
            titulo="Leche",
            subtitulo="Estación de ordeño: medición en vivo y producción de hoy",
            icono=ft.Icons.WATER_DROP,
        )

    # =============================================================
    # Construcción
    # =============================================================
    def construir(self):
        return [
            ft.ResponsiveRow(spacing=16, run_spacing=16, controls=[
                self._tarjeta_balde(), self._tarjeta_estabilidad(),
            ]),
            self._tarjetas_resumen(),
            self._tarjeta_ordenos_hoy(),
        ]

    def _tarjeta_balde(self):
        self.balde = IndicadorBalde(config.CAPACIDAD_BALDE_KG)
        self.texto_litros = ft.Text("0.00 L", size=40, weight=ft.FontWeight.BOLD, color=config.AZUL)
        self.texto_kg = ft.Text("", size=14, color=config.TEXTO_SEC)
        self.chip_estable = Chip("Estable", config.VERDE)
        self.texto_accion = ft.Text("", size=12, color=config.TEXTO_SEC)
        tarjeta = self.tarjeta(ft.Column(spacing=14, controls=[
            self.titulo_tarjeta("Leche en el balde", ft.Icons.WATER_DROP, config.AZUL),
            ft.Row(spacing=24, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                self.balde.control,
                ft.Column(spacing=8, expand=True, controls=[
                    self.texto_litros, self.texto_kg, self.chip_estable.control,
                ]),
            ]),
            self.texto_accion,
        ]))
        tarjeta.col = {"xs": 12, "lg": 5}
        return tarjeta

    def _tarjeta_estabilidad(self):
        self.grafica_lecturas = GraficaLineas(
            series=[("Lecturas de la balanza (10 por segundo)", config.AZUL, False)],
            alto=170, decimales=3, curvas=False, rango_minimo=0.1,
        )
        self.texto_regla = ft.Text("", size=13, color=config.TEXTO)
        self.texto_ultimas = ft.Text("", size=12, color=config.TEXTO_SEC, font_family="monospace")
        tarjeta = self.tarjeta(ft.Column(spacing=12, controls=[
            self.titulo_tarjeta("¿El peso está estable?", ft.Icons.INSIGHTS, config.AZUL),
            self.grafica_lecturas.control,
            self.texto_regla,
            self.texto_ultimas,
        ]))
        tarjeta.col = {"xs": 12, "lg": 7}
        return tarjeta

    def _tarjetas_resumen(self):
        col = {"xs": 6, "md": 3}
        self.tarjeta_ordenos = TarjetaDato("Ordeños de hoy", ft.Icons.FORMAT_LIST_NUMBERED, "", config.AZUL, col)
        self.tarjeta_total = TarjetaDato("Litros de hoy", ft.Icons.LOCAL_DRINK, "L", config.AZUL, col)
        self.tarjeta_promedio = TarjetaDato("Promedio por ordeño", ft.Icons.EQUALIZER, "L", config.TEXTO_SEC, col)
        self.tarjeta_ultimo = TarjetaDato("Último ordeño", ft.Icons.SCHEDULE, "L", config.ACENTO, col)
        return ft.ResponsiveRow(spacing=16, run_spacing=16, controls=[
            self.tarjeta_ordenos.control, self.tarjeta_total.control,
            self.tarjeta_promedio.control, self.tarjeta_ultimo.control,
        ])

    def _tarjeta_ordenos_hoy(self):
        self.lista_hoy = ft.Column(spacing=8)
        return self.tarjeta(ft.Column(spacing=12, controls=[
            self.titulo_tarjeta("Ordeños de hoy", ft.Icons.TODAY, config.AZUL),
            self.lista_hoy,
        ]))

    # =============================================================
    # Actualización periódica
    # =============================================================
    def actualizar(self, d):
        self._actualizar_balde(d)
        self._actualizar_estabilidad(d)
        self._actualizar_resumen(d)

    def _actualizar_balde(self, d):
        kg = d["kg"] if abs(d["kg"]) >= 0.005 else 0.0      # Evita mostrar "-0.00"
        self.balde.actualizar(kg)
        self.texto_litros.value = f"{d['litros']:.2f} L"
        self.texto_kg.value = f"{kg:.2f} kg ÷ {config.DENSIDAD_LECHE} kg/L"
        if d["estable"] and d["litros"] > 0.05:
            self.chip_estable.actualizar("Peso estable: listo para registrar", config.VERDE)
            self.texto_accion.value = "Presione el pulsador de la balanza para guardar el ordeño."
        elif d["estable"]:
            self.chip_estable.actualizar("Balde vacío", config.TEXTO_SEC)
            self.texto_accion.value = "Esperando que se vierta la leche."
        else:
            self.chip_estable.actualizar("Leche en movimiento", config.AMARILLO)
            self.texto_accion.value = "Espere a que el peso se estabilice antes de registrar."

    def _actualizar_estabilidad(self, d):
        self.grafica_lecturas.actualizar([d["lecturas_kg"]])
        ultimas = d["ultimas_lecturas"]
        if len(ultimas) < config.MUESTRAS_ESTABILIDAD:
            self.texto_regla.value = "Reuniendo lecturas…"
            return
        diferencia = max(ultimas) - min(ultimas)
        tolerancia = d["tolerancia_kg"]
        signo, resultado, color = ("<", "estable", config.VERDE) if diferencia < tolerancia \
            else ("≥", "no estable", config.AMARILLO)
        self.texto_regla.value = (f"Máx − mín de las últimas {len(ultimas)} lecturas = {diferencia * 1000:.0f} g "
                                  f"{signo} {tolerancia * 1000:.0f} g  →  {resultado}")
        self.texto_regla.color = color
        self.texto_ultimas.value = "  ".join(f"{v:.3f}" for v in ultimas) + "  kg"

    def _actualizar_resumen(self, d):
        registros = d["registros"]
        hoy = [r for r in registros if r["fecha"].date() == datetime.now().date()]
        semana = [r for r in registros if r["fecha"] >= datetime.now() - timedelta(days=7)]

        self.tarjeta_ordenos.actualizar(str(len(hoy)), "Registrados con el pulsador")
        self.tarjeta_total.actualizar(f"{sum(r['litros'] for r in hoy):.2f}", "Suma de los ordeños de hoy")
        if semana:
            promedio = sum(r["litros"] for r in semana) / len(semana)
            self.tarjeta_promedio.actualizar(f"{promedio:.2f}", f"Últimos 7 días ({len(semana)} ordeños)")
        if registros:
            ultimo = registros[-1]
            self.tarjeta_ultimo.actualizar(f"{ultimo['litros']:.2f}", f"{ultimo['fecha']:%d/%m %H:%M}")

        # La lista solo se reconstruye cuando hay un ordeño nuevo
        if len(hoy) == self._ordenos_mostrados:
            return
        self._ordenos_mostrados = len(hoy)
        if not hoy:
            self.lista_hoy.controls = [ft.Text("Todavía no hay ordeños hoy.", size=13, color=config.TEXTO_SEC)]
            return
        self.lista_hoy.controls = [self._fila_ordeno(r) for r in reversed(hoy)]

    def _fila_ordeno(self, r):
        origen = {"pulsador": "Pulsador", "escenario": "Escenario"}.get(r.get("origen"), "")
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=12, vertical=10),
            border_radius=10,
            bgcolor=config.PANEL_2,
            content=ft.Row(spacing=16, controls=[
                ft.Text(f"#{r['ordeno']}", size=13, weight=ft.FontWeight.BOLD, color=config.AZUL, width=40),
                ft.Text(f"{r['fecha']:%H:%M:%S}", size=13, color=config.TEXTO, width=80),
                ft.Text(f"{r['litros']:.2f} L", size=13, weight=ft.FontWeight.W_600, color=config.TEXTO, expand=True),
                ft.Text(origen, size=12, color=config.TEXTO_SEC),
            ]),
        )
