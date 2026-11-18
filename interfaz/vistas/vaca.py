# vistas/vaca.py
# Pantalla Vaca: todo lo del collar (MPU6050) y la detección de posible celo.
# La leche tiene su propia pantalla: aquí solo está lo que importa del animal.
#
# Organización (ResponsiveRow = gestor de geometría adaptable de 12 columnas):
#   Fila 1: estado (semáforo)           |  4 tarjetas de variables
#   Fila 2: gráfica de actividad        |  medidor de la razón
#   Fila 3: movimiento instantáneo (ancho completo)
# En pantallas angostas cada tarjeta ocupa el ancho completo.

import flet as ft
import config
from vistas.base import VistaBase
from componentes.tarjetas import TarjetaDato, Chip
from componentes.semaforo import SemaforoVisual
from componentes.graficas import GraficaLineas
from componentes.medidor import MedidorRazon

# Cuántas columnas (de 12) ocupa cada bloque según el ancho de pantalla
ANCHO_GRANDE = {"xs": 12, "lg": 8}
ANCHO_PEQUENO = {"xs": 12, "lg": 4}


class VistaVaca(VistaBase):

    def __init__(self):
        super().__init__(
            titulo="Vaca 01",
            subtitulo="Actividad medida por el collar y detección de posible celo",
            icono=ft.Icons.SENSORS,
        )

    # =============================================================
    # Construcción de la pantalla
    # =============================================================
    def construir(self):
        return [
            ft.ResponsiveRow(spacing=16, run_spacing=16, controls=[
                self._tarjeta_estado(), self._tarjetas_variables(),
            ]),
            ft.ResponsiveRow(spacing=16, run_spacing=16, controls=[
                self._tarjeta_grafica_actividad(), self._tarjeta_medidor(),
            ]),
            self._tarjeta_movimiento(),
        ]

    def _tarjeta_estado(self):
        self.semaforo = SemaforoVisual()
        self.texto_estado = ft.Text("Calibrando", size=30, weight=ft.FontWeight.BOLD, color=config.TEXTO_SEC)
        self.texto_explicacion = ft.Text("", size=13, color=config.TEXTO_SEC)
        # Barras de progreso: calibración y ventana actual
        self.texto_calibracion = ft.Text("", size=12, color=config.TEXTO_SEC)
        self.barra_calibracion = ft.ProgressBar(value=0, color=config.ACENTO, bgcolor=config.PANEL_2,
                                                bar_height=6, border_radius=3)
        self.bloque_calibracion = ft.Column(spacing=6, controls=[self.texto_calibracion, self.barra_calibracion])
        self.texto_ventana = ft.Text("", size=12, color=config.TEXTO_SEC)
        self.barra_ventana = ft.ProgressBar(value=0, color=config.MORADO, bgcolor=config.PANEL_2,
                                            bar_height=6, border_radius=3)
        self.texto_motivo = ft.Text("", size=12, color=config.TEXTO_SEC, italic=True)
        tarjeta = self.tarjeta(ft.Column(spacing=14, controls=[
            self.titulo_tarjeta("Estado de la vaca", ft.Icons.SENSORS),
            self.semaforo.control,
            self.texto_estado,
            self.texto_explicacion,
            self.bloque_calibracion,
            ft.Column(spacing=6, controls=[self.texto_ventana, self.barra_ventana, self.texto_motivo]),
        ]))
        tarjeta.col = ANCHO_PEQUENO
        return tarjeta

    def _tarjetas_variables(self):
        col = {"xs": 6, "md": 3, "lg": 6}
        self.tarjeta_actividad = TarjetaDato("Actividad", ft.Icons.DIRECTIONS_RUN, "g", config.ACENTO, col)
        self.tarjeta_base = TarjetaDato("Línea base", ft.Icons.HORIZONTAL_RULE, "g", config.TEXTO_SEC, col)
        self.tarjeta_razon = TarjetaDato("Razón", ft.Icons.SPEED, "× lo normal", config.AMARILLO, col)
        self.tarjeta_umbral = TarjetaDato("Umbral de celo", ft.Icons.FLAG, "×", config.ROJO, col)
        return ft.Container(
            col=ANCHO_GRANDE,
            content=ft.ResponsiveRow(spacing=16, run_spacing=16, controls=[
                self.tarjeta_actividad.control, self.tarjeta_base.control,
                self.tarjeta_razon.control, self.tarjeta_umbral.control,
            ]),
        )

    def _tarjeta_grafica_actividad(self):
        self.grafica_actividad = GraficaLineas(
            series=[
                ("Actividad por ventana", config.ACENTO, False),
                ("Línea base", config.TEXTO_SEC, True),
                ("Umbral actividad alta", config.AMARILLO, True),
                ("Umbral de celo", config.ROJO, True),
            ],
            alto=240, decimales=3, puntos_visibles=True,
        )
        tarjeta = self.tarjeta(ft.Column(spacing=12, controls=[
            self.titulo_tarjeta("Actividad por ventana de 10 s (últimos 5 min)", ft.Icons.SHOW_CHART),
            self.grafica_actividad.control,
        ]))
        tarjeta.col = ANCHO_GRANDE
        return tarjeta

    def _tarjeta_medidor(self):
        self.medidor = MedidorRazon()
        self.texto_reglas = ft.Text("", size=12, color=config.TEXTO_SEC)
        tarjeta = self.tarjeta(ft.Column(spacing=16, controls=[
            self.titulo_tarjeta("¿Qué tan lejos está de cada umbral?", ft.Icons.SPEED),
            self.medidor.control,
            ft.Divider(height=1, color=config.BORDE),
            self.texto_reglas,
        ]))
        tarjeta.col = ANCHO_PEQUENO
        return tarjeta

    def _tarjeta_movimiento(self):
        self.grafica_movimiento = GraficaLineas(
            series=[("| |a| − 1 g | de cada muestra (10 por segundo)", config.MORADO, False)],
            alto=150, decimales=2, curvas=False,
        )
        self.chip_pico = Chip("Pico de movimiento", config.AMARILLO, ft.Icons.BOLT)
        self.chip_pico.control.visible = False
        self.texto_picos = ft.Text("", size=12, color=config.TEXTO_SEC)
        return self.tarjeta(ft.Column(spacing=12, controls=[
            self.titulo_tarjeta("Movimiento instantáneo (últimos 10 s)", ft.Icons.VIBRATION),
            ft.Row(wrap=True, spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                self.chip_pico.control,
                self.texto_picos,
            ]),
            self.grafica_movimiento.control,
        ]))

    # =============================================================
    # Actualización periódica (la llama la aplicación cada 0.5 s)
    # =============================================================
    def actualizar(self, d):
        self._actualizar_estado(d)
        self._actualizar_variables(d)
        self._actualizar_graficas(d)
        self._actualizar_medidor(d)

    def _actualizar_estado(self, d):
        estado = d["estado"]
        self.semaforo.mostrar(estado)
        self.texto_estado.value = config.NOMBRE_ESTADO[estado]
        self.texto_estado.color = config.COLOR_ESTADO[estado]
        if d["calibrando"]:
            self.texto_explicacion.value = "Aprendiendo la actividad normal de la vaca. No se generan alertas."
        elif estado == config.ESTADO_CELO:
            self.texto_explicacion.value = (f"Se mueve {d['razon']:.1f} veces más de lo normal. "
                                            "Confirme observando al animal.")
        elif estado == config.ESTADO_ALTA:
            self.texto_explicacion.value = f"Se mueve {d['razon']:.1f} veces lo normal. Vigilar."
        else:
            self.texto_explicacion.value = "Actividad dentro de lo normal."

        self.bloque_calibracion.visible = d["calibrando"]
        ventanas = round(d["progreso_calibracion"] * config.VENTANAS_CALIBRACION)
        self.texto_calibracion.value = f"Calibrando línea base: {ventanas} de {config.VENTANAS_CALIBRACION} ventanas"
        self.barra_calibracion.value = d["progreso_calibracion"]

        self.texto_ventana.value = (f"Próxima evaluación en {d['segundos_para_evaluar']:.0f} s"
                                    f" · {d['muestras_ventana']} muestras en esta ventana")
        self.barra_ventana.value = d["progreso_ventana"]
        self.texto_motivo.value = f"Última evaluación: {d['motivo']}"

    def _actualizar_variables(self, d):
        if d["calibrando"]:
            # Mientras calibra, la línea base todavía no es real (vale el mínimo
            # LINEA_BASE_MINIMA): mostrarla confundiría al usuario.
            self.tarjeta_actividad.actualizar("--", "Esperando la primera ventana")
            self.tarjeta_razon.actualizar("--", "Disponible al terminar la calibración")
            self.tarjeta_base.actualizar("--", "Se calcula con las 3 primeras ventanas")
        else:
            self.tarjeta_actividad.actualizar(f"{d['actividad']:.4f}", "Promedio de la última ventana")
            self.tarjeta_razon.actualizar(f"{d['razon']:.2f}", "Actividad ÷ línea base",
                                          config.COLOR_ESTADO[d["estado"]])
            self.tarjeta_base.actualizar(f"{d['linea_base']:.4f}", "Lo normal para esta vaca")
        self.tarjeta_umbral.actualizar(f"{d['umbral_celo']:.2f}",
                                       f"Actividad alta desde {d['umbral_alta']:.1f}")

    def _actualizar_graficas(self, d):
        ventanas = d["ventanas"]
        self.grafica_actividad.actualizar([
            [v["actividad"] for v in ventanas],
            [v["linea_base"] for v in ventanas],
            [v["linea_base"] * d["umbral_alta"] for v in ventanas],
            [v["linea_base"] * d["umbral_celo"] for v in ventanas],
        ])
        self.grafica_movimiento.actualizar([d["movimientos"]])
        self.chip_pico.control.visible = d["en_pico"]
        if d["espontaneos"] or d["picos"]:
            self.texto_picos.value = f"{d['picos']} picos espontáneos desde el inicio"

    def _actualizar_medidor(self, d):
        self.medidor.actualizar(d["razon"], d["umbral_alta"], d["umbral_celo"], visible=not d["calibrando"])
        m = d["margen"]
        self.texto_reglas.value = (
            f"Sube a amarillo con {d['umbral_alta']:g} y a rojo con {d['umbral_celo']:g}.\n"
            f"Para bajar, la razón debe quedar {m:g} por debajo del umbral "
            f"(histéresis): vuelve a amarillo con menos de {d['umbral_celo'] - m:g} "
            f"y a verde con menos de {d['umbral_alta'] - m:g}."
        )
