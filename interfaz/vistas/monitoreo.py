# vistas/monitoreo.py
# Pantalla de Monitoreo: muestra en tiempo real el estado de la vaca,
# las variables de actividad, las gráficas y el balde de leche.
#
# Organización (ResponsiveRow = gestor de geometría adaptable):
#   Fila 1: tarjeta de estado (semáforo)  |  4 tarjetas de variables
#   Fila 2: gráfica de actividad          |  balde de leche
#   Fila 3: movimiento instantáneo        |  último mensaje MQTT
# En pantallas angostas cada tarjeta ocupa el ancho completo.

from datetime import datetime

import flet as ft
import config
from vistas.base import VistaBase
from componentes.tarjetas import TarjetaDato, Chip
from componentes.semaforo import SemaforoVisual
from componentes.graficas import GraficaLineas
from componentes.balde import IndicadorBalde

# Cuántas columnas (de 12) ocupa cada bloque según el ancho de pantalla
ANCHO_GRANDE = {"xs": 12, "lg": 8}
ANCHO_PEQUENO = {"xs": 12, "lg": 4}


class VistaMonitoreo(VistaBase):

    def __init__(self):
        super().__init__(
            titulo="Monitoreo",
            subtitulo="Estado de la vaca y de la leche en tiempo real",
            icono=ft.Icons.MONITOR_HEART,
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
                self._tarjeta_grafica_actividad(), self._tarjeta_leche(),
            ]),
            ft.ResponsiveRow(spacing=16, run_spacing=16, controls=[
                self._tarjeta_movimiento(), self._tarjeta_mqtt(),
            ]),
        ]

    def _titulo_tarjeta(self, texto, icono):
        return ft.Row(spacing=8, controls=[
            ft.Icon(icono, size=18, color=config.ACENTO),
            ft.Text(texto, size=15, weight=ft.FontWeight.W_600, color=config.TEXTO),
        ])

    def _tarjeta_estado(self):
        self.semaforo = SemaforoVisual()
        self.texto_estado = ft.Text("Calibrando", size=30, weight=ft.FontWeight.BOLD, color=config.TEXTO_SEC)
        self.texto_explicacion = ft.Text("Aprendiendo la actividad normal de la vaca…",
                                         size=13, color=config.TEXTO_SEC)
        # Barras de progreso: calibración y ventana actual
        self.texto_calibracion = ft.Text("", size=12, color=config.TEXTO_SEC)
        self.barra_calibracion = ft.ProgressBar(value=0, color=config.ACENTO, bgcolor=config.PANEL_2,
                                                bar_height=6, border_radius=3)
        self.bloque_calibracion = ft.Column(spacing=6, controls=[self.texto_calibracion, self.barra_calibracion])
        self.texto_ventana = ft.Text("", size=12, color=config.TEXTO_SEC)
        self.texto_motivo = ft.Text("", size=12, color=config.TEXTO_SEC, italic=True)
        self.barra_ventana = ft.ProgressBar(value=0, color=config.MORADO, bgcolor=config.PANEL_2,
                                            bar_height=6, border_radius=3)
        tarjeta = self.tarjeta(ft.Column(spacing=14, controls=[
            self._titulo_tarjeta("Estado de la vaca", ft.Icons.SENSORS),
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
            self._titulo_tarjeta("Actividad por ventana de 10 s (últimos 5 min)", ft.Icons.SHOW_CHART),
            self.grafica_actividad.control,
        ]))
        tarjeta.col = ANCHO_GRANDE
        return tarjeta

    def _tarjeta_leche(self):
        self.balde = IndicadorBalde(config.CAPACIDAD_BALDE_KG)
        self.texto_litros = ft.Text("0.00 L", size=30, weight=ft.FontWeight.BOLD, color=config.AZUL)
        self.texto_kg = ft.Text("0.00 kg", size=14, color=config.TEXTO_SEC)
        self.chip_estable = Chip("Estable", config.VERDE)
        self.texto_ultimo = ft.Text("", size=12, color=config.TEXTO_SEC)
        self.texto_hoy = ft.Text("", size=12, color=config.TEXTO_SEC)
        tarjeta = self.tarjeta(ft.Column(spacing=14, controls=[
            self._titulo_tarjeta("Leche en el balde", ft.Icons.WATER_DROP),
            ft.Row(spacing=20, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                self.balde.control,
                ft.Column(spacing=8, controls=[
                    self.texto_litros, self.texto_kg, self.chip_estable.control,
                ]),
            ]),
            ft.Divider(height=1, color=config.BORDE),
            self.texto_ultimo,
            self.texto_hoy,
        ]))
        tarjeta.col = ANCHO_PEQUENO
        return tarjeta

    def _tarjeta_movimiento(self):
        self.grafica_movimiento = GraficaLineas(
            series=[("| |a| − 1 g | de cada muestra (10 por segundo)", config.MORADO, False)],
            alto=150, decimales=2, curvas=False,
        )
        tarjeta = self.tarjeta(ft.Column(spacing=12, controls=[
            self._titulo_tarjeta("Movimiento instantáneo (últimos 10 s)", ft.Icons.VIBRATION),
            self.grafica_movimiento.control,
        ]))
        tarjeta.col = ANCHO_GRANDE
        return tarjeta

    def _tarjeta_mqtt(self):
        self.texto_topico = ft.Text("", size=12, color=config.MORADO, selectable=True)
        self.texto_carga = ft.Text("", size=13, font_family="monospace", color=config.TEXTO, selectable=True)
        self.texto_hora_mqtt = ft.Text("", size=11, color=config.TEXTO_SEC)
        self.chip_conexion = Chip("Conectado", config.VERDE)
        tarjeta = self.tarjeta(ft.Column(spacing=10, controls=[
            self._titulo_tarjeta("Último mensaje MQTT", ft.Icons.WIFI_TETHERING),
            self.chip_conexion.control,
            self.texto_topico,
            ft.Container(
                padding=10, border_radius=8, bgcolor=config.FONDO,
                content=self.texto_carga,
            ),
            self.texto_hora_mqtt,
        ]))
        tarjeta.col = ANCHO_PEQUENO
        return tarjeta

    # =============================================================
    # Actualización periódica (la llama la aplicación cada 0.5 s)
    # =============================================================
    def actualizar(self, d):
        self._actualizar_estado(d)
        self._actualizar_variables(d)
        self._actualizar_graficas(d)
        self._actualizar_leche(d)
        self._actualizar_mqtt(d)

    def _actualizar_estado(self, d):
        estado = d["estado"]
        color = config.COLOR_ESTADO[estado]
        self.semaforo.mostrar(estado)
        self.texto_estado.value = config.NOMBRE_ESTADO[estado]
        self.texto_estado.color = color
        if d["calibrando"]:
            self.texto_explicacion.value = "Aprendiendo la actividad normal de la vaca. No se generan alertas."
        elif estado == config.ESTADO_CELO:
            self.texto_explicacion.value = f"Se mueve {d['razon']:.1f} veces más de lo normal. Confirme observando al animal."
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
            self.tarjeta_actividad.actualizar("--", "Esperando la primera ventana")
            self.tarjeta_razon.actualizar("--", "Disponible al terminar la calibración")
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

    def _actualizar_leche(self, d):
        self.balde.actualizar(d["kg"])
        self.texto_litros.value = f"{d['litros']:.2f} L"
        kg = d["kg"] if abs(d["kg"]) >= 0.005 else 0.0     # Evita mostrar "-0.00"
        self.texto_kg.value = f"{kg:.2f} kg ÷ {config.DENSIDAD_LECHE}"
        if d["estable"]:
            self.chip_estable.actualizar("Peso estable", config.VERDE)
        else:
            self.chip_estable.actualizar("Leche en movimiento", config.AMARILLO)

        registros = d["registros"]
        if registros:
            ultimo = registros[-1]
            self.texto_ultimo.value = (f"Último ordeño: #{ultimo['ordeno']} · {ultimo['litros']:.2f} L"
                                       f" · {ultimo['fecha']:%d/%m %H:%M}")
        hoy = [r for r in registros if r["fecha"].date() == datetime.now().date()]
        self.texto_hoy.value = f"Hoy: {len(hoy)} ordeños · {sum(r['litros'] for r in hoy):.2f} L"

    def _actualizar_mqtt(self, d):
        if d["conectado"]:
            self.chip_conexion.actualizar("Conectado al broker (simulado)", config.VERDE)
        else:
            self.chip_conexion.actualizar("Sin conexión: los datos no se envían", config.ROJO)
        if d["mensajes"]:
            ultimo = d["mensajes"][-1]
            self.texto_topico.value = ultimo["topico"]
            self.texto_carga.value = ultimo["carga"]
            self.texto_hora_mqtt.value = f"{ultimo['fecha']:%H:%M:%S} · {len(d['mensajes'])} mensajes recientes"
