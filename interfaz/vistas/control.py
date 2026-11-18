# vistas/control.py
# Pantalla de Control. Tiene dos partes bien separadas:
#
#   1. SIMULACIÓN: reemplaza a los sensores mientras no hay ESP32.
#      Comportamiento de la vaca, escenario de demostración, reloj y balde.
#   2. COMANDOS A LA ESP32: los mismos 5 comandos MQTT del firmware.
#      Cada campo de texto se VALIDA antes de enviar.
#
# Eventos usados:
#   on_click   -> botones (equivale al command de Tkinter)
#   on_change  -> se ejecuta en cada tecla o movimiento (equivale a bind)
#   on_submit  -> al presionar Enter en un campo (equivale a bind('<Return>'))
#   on_select  -> al elegir una opción de la lista desplegable

import flet as ft
import config
from vistas.base import VistaBase
from componentes.escenario import LineaTiempoEscenario
from validacion import validar_decimal


class VistaControl(VistaBase):

    def __init__(self, simulador, al_cambiar, notificar):
        # Se guardan ANTES de super().__init__, porque construir() los usa
        self.simulador = simulador
        self.al_cambiar = al_cambiar       # Refresca la aplicación
        self.notificar = notificar         # Muestra un mensaje (SnackBar)
        super().__init__(
            titulo="Control",
            subtitulo="Simulación de los sensores y comandos para la ESP32",
            icono=ft.Icons.TUNE,
        )

    # =============================================================
    # Construcción
    # =============================================================
    def construir(self):
        return [
            self._encabezado_seccion("Simulación", "Reemplaza a los sensores mientras no hay ESP32 conectada",
                                     ft.Icons.SCIENCE, config.MORADO),
            ft.ResponsiveRow(spacing=16, run_spacing=16, controls=[
                self._tarjeta_vaca(), self._tarjeta_balanza(),
            ]),
            self._encabezado_seccion("Comandos a la ESP32", "Se envían por MQTT; los mismos que recibe el firmware",
                                     ft.Icons.SETTINGS_REMOTE, config.ACENTO),
            ft.ResponsiveRow(spacing=16, run_spacing=16, controls=[
                self._comando_umbral(), self._comando_calibrar(), self._comando_intervalo(),
                self._comando_tara(), self._comando_buzzer(),
            ]),
        ]

    def _encabezado_seccion(self, titulo, subtitulo, icono, color):
        return ft.Row(spacing=10, controls=[
            ft.Icon(icono, color=color, size=22),
            ft.Column(spacing=0, expand=True, controls=[
                ft.Text(titulo, size=18, weight=ft.FontWeight.BOLD, color=config.TEXTO),
                ft.Text(subtitulo, size=12, color=config.TEXTO_SEC),
            ]),
        ])

    def _subtitulo(self, texto):
        return ft.Text(texto, size=13, weight=ft.FontWeight.W_600, color=config.TEXTO_SEC)

    # ---------- Simulación: la vaca ----------
    def _tarjeta_vaca(self):
        self.selector_modo = ft.SegmentedButton(
            selected=[config.MODO_MANUAL],
            on_change=self._al_cambiar_modo,
            segments=[
                ft.Segment(value=config.MODO_MANUAL, label="Manual", icon=ft.Icons.PAN_TOOL_ALT),
                ft.Segment(value=config.MODO_ESCENARIO, label="Escenario de demostración",
                           icon=ft.Icons.SMART_DISPLAY),
            ],
        )

        # Panel manual
        self.selector_comportamiento = ft.SegmentedButton(
            selected=["reposo"],
            allow_empty_selection=True,     # Vacío = movimiento personalizado
            on_change=self._al_elegir_comportamiento,
            segments=[
                ft.Segment(value="reposo", label=config.COMPORTAMIENTOS["reposo"][0], icon=ft.Icons.GRASS),
                ft.Segment(value="inquieta", label=config.COMPORTAMIENTOS["inquieta"][0], icon=ft.Icons.DIRECTIONS_WALK),
                ft.Segment(value="celo", label=config.COMPORTAMIENTOS["celo"][0], icon=ft.Icons.DIRECTIONS_RUN),
            ],
        )
        self.texto_comportamiento = ft.Text("", size=12, color=config.TEXTO_SEC)
        self.deslizador_movimiento = ft.Slider(
            min=0, max=config.MOVIMIENTO_MAXIMO, divisions=60,
            value=config.COMPORTAMIENTOS["reposo"][1], label="{value} g",
            active_color=config.ACENTO,
            on_change_end=self._al_mover_deslizador,
        )
        self.panel_manual = ft.Column(spacing=8, controls=[
            self._subtitulo("Comportamiento de la vaca"),
            self.selector_comportamiento,
            self.texto_comportamiento,
            self._subtitulo("Ajuste fino del movimiento"),
            self.deslizador_movimiento,
            ft.Row(spacing=6, controls=[
                ft.Icon(ft.Icons.INFO_OUTLINE, size=14, color=config.TEXTO_SEC),
                ft.Text("El estado se evalúa al cerrar cada ventana de 10 s: "
                        "un cambio se ve en la siguiente evaluación.",
                        size=12, color=config.TEXTO_SEC, expand=True),
            ]),
        ])

        # Panel del escenario
        self.linea_tiempo = LineaTiempoEscenario()
        self.panel_escenario = ft.Column(visible=False, spacing=10, controls=[
            self._subtitulo("Avance del escenario"),
            self.linea_tiempo.control,
            ft.Row(spacing=10, controls=[
                ft.OutlinedButton(content="Reiniciar escenario", icon=ft.Icons.REPLAY,
                                  on_click=self._reiniciar_escenario),
                ft.OutlinedButton(content="Detener", icon=ft.Icons.STOP, on_click=self._detener_escenario),
            ]),
        ])

        # Reloj de la simulación
        self.selector_reloj = ft.Dropdown(
            label="Reloj de la simulación",
            value="1",
            width=260,
            options=[ft.DropdownOption(key=str(v), text=f"×{v}" + (" (tiempo real)" if v == 1 else ""))
                     for v in config.VELOCIDADES],
            on_select=self._al_cambiar_reloj,
        )

        tarjeta = self.tarjeta(ft.Column(spacing=16, controls=[
            self._titulo_tarjeta("Vaca 01 (collar con MPU6050)", ft.Icons.SENSORS),
            self.selector_modo,
            self.panel_manual,
            self.panel_escenario,
            ft.Divider(height=1, color=config.BORDE),
            ft.Row(wrap=True, spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                self.selector_reloj,
                ft.Text("Acelera el tiempo, no el movimiento de la vaca.", size=12, color=config.TEXTO_SEC),
            ]),
        ]))
        tarjeta.col = {"xs": 12, "lg": 7}
        return tarjeta

    # ---------- Simulación: la balanza ----------
    def _tarjeta_balanza(self):
        self.deslizador_carga = ft.Slider(
            min=0, max=config.CAPACIDAD_BALDE_KG, divisions=80, value=0,
            label="{value} kg", active_color=config.AZUL,
            on_change_end=self._al_mover_carga,
        )
        self.texto_lectura = ft.Text("", size=14, color=config.TEXTO)
        self.texto_estabilidad = ft.Text("", size=12, color=config.TEXTO_SEC)
        tarjeta = self.tarjeta(ft.Column(spacing=14, controls=[
            self._titulo_tarjeta("Balanza (celda de carga + HX711)", ft.Icons.SCALE),
            self._subtitulo("Leche que se vierte en el balde"),
            self.deslizador_carga,
            self.texto_lectura,
            self.texto_estabilidad,
            ft.FilledButton(
                content="Presionar el pulsador: registrar ordeño",
                icon=ft.Icons.TOUCH_APP,
                on_click=self._registrar_ordeno,
            ),
            ft.Text("Solo se registra si el peso está estable, igual que en el firmware.",
                    size=12, color=config.TEXTO_SEC),
        ]))
        tarjeta.col = {"xs": 12, "lg": 5}
        return tarjeta

    # ---------- Comandos ----------
    def _tarjeta_comando(self, titulo, icono, topico, contenido):
        tarjeta = self.tarjeta(ft.Column(spacing=12, controls=[
            self._titulo_tarjeta(titulo, icono),
            *contenido,
            ft.Text(f"Tópico: {topico.replace(config.PREFIJO + '/', '')}", size=11,
                    color=config.MORADO, selectable=True),
        ]), padding=16)
        tarjeta.col = {"xs": 12, "md": 6, "xl": 4}
        return tarjeta

    def _comando_umbral(self):
        self.campo_umbral = ft.TextField(
            label="Umbral de celo",
            value=f"{config.UMBRAL_CELO:.2f}",
            suffix="× lo normal",
            helper=f"Mayor que {config.UMBRAL_ACTIVIDAD_ALTA} y hasta {config.UMBRAL_CELO_MAXIMO}",
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._validar_umbral,      # Valida mientras se escribe
            on_submit=self._enviar_umbral,       # Enter envía
            dense=True,
        )
        self.boton_umbral = ft.FilledButton(content="Enviar", icon=ft.Icons.SEND, on_click=self._enviar_umbral)
        return self._tarjeta_comando("Umbral de celo", ft.Icons.FLAG, config.TOPICO_CFG_UMBRAL, [
            self.campo_umbral, self.boton_umbral,
        ])

    def _comando_calibrar(self):
        self.campo_peso = ft.TextField(
            label="Peso conocido sobre la balanza",
            value="",
            hint_text="Ej.: 10",
            suffix="kg",
            helper=f"Entre 0.1 y {config.PESO_CALIBRACION_MAXIMO:g} kg",
            keyboard_type=ft.KeyboardType.NUMBER,
            on_change=self._validar_peso,
            on_submit=self._enviar_calibracion,
            dense=True,
        )
        self.boton_calibrar = ft.FilledButton(content="Calibrar", icon=ft.Icons.TUNE,
                                              on_click=self._enviar_calibracion, disabled=True)
        return self._tarjeta_comando("Calibrar balanza", ft.Icons.SCALE, config.TOPICO_CMD_CALIBRAR, [
            self.campo_peso, self.boton_calibrar,
        ])

    def _comando_intervalo(self):
        self.selector_intervalo = ft.Dropdown(
            label="Enviar el peso cada",
            value=str(config.INTERVALO_PUBLICACION_MS),
            options=[ft.DropdownOption(key=str(ms), text=f"{ms / 1000:g} s")
                     for ms in config.INTERVALOS_PUBLICACION_MS],
            on_select=self._enviar_intervalo,
        )
        return self._tarjeta_comando("Intervalo de publicación", ft.Icons.TIMER,
                                     config.TOPICO_CFG_MUESTREO, [self.selector_intervalo])

    def _comando_tara(self):
        return self._tarjeta_comando("Tara", ft.Icons.EXPOSURE_ZERO, config.TOPICO_CMD_TARA, [
            ft.Text("Pone la balanza en cero. Hágalo con el balde vacío.", size=12, color=config.TEXTO_SEC),
            ft.OutlinedButton(content="Hacer tara", icon=ft.Icons.EXPOSURE_ZERO, on_click=self._enviar_tara),
        ])

    def _comando_buzzer(self):
        self.interruptor_buzzer = ft.Switch(label="Silenciar buzzer", value=False,
                                            on_change=self._enviar_buzzer)
        return self._tarjeta_comando("Alarma sonora", ft.Icons.VOLUME_UP, config.TOPICO_CMD_BUZZER, [
            ft.Text("Silencia la alarma del episodio actual. Vuelve a sonar en el siguiente.",
                    size=12, color=config.TEXTO_SEC),
            self.interruptor_buzzer,
        ])

    def _titulo_tarjeta(self, texto, icono):
        return ft.Row(spacing=8, controls=[
            ft.Icon(icono, size=18, color=config.ACENTO),
            ft.Text(texto, size=15, weight=ft.FontWeight.W_600, color=config.TEXTO, expand=True),
        ])

    # =============================================================
    # Eventos de la simulación
    # =============================================================
    def _al_cambiar_modo(self, e):
        if e.control.selected[0] == config.MODO_ESCENARIO:
            self.simulador.iniciar_escenario()
            self.notificar("Escenario iniciado: siga la línea de tiempo")
        else:
            self.simulador.detener_escenario()
            self.notificar("Modo manual: la vaca queda en reposo")
        self.al_cambiar()

    def _al_elegir_comportamiento(self, e):
        clave = e.control.selected[0]
        self.simulador.fijar_comportamiento(clave)
        self.deslizador_movimiento.value = config.COMPORTAMIENTOS[clave][1]
        self.notificar(f"La vaca pasa a «{config.COMPORTAMIENTOS[clave][0]}». "
                       "El estado cambia en la próxima evaluación.")
        self.al_cambiar()

    def _al_mover_deslizador(self, e):
        self.simulador.fijar_movimiento(float(e.control.value))
        self.al_cambiar()

    def _al_cambiar_reloj(self, e):
        self.simulador.cambiar_velocidad(int(e.control.value))
        self.notificar(f"Reloj de la simulación ×{e.control.value}")
        self.al_cambiar()

    def _reiniciar_escenario(self, e):
        self.simulador.iniciar_escenario()
        self.notificar("Escenario reiniciado desde la fase 1")
        self.al_cambiar()

    def _detener_escenario(self, e):
        self.simulador.detener_escenario()
        self.al_cambiar()

    def _al_mover_carga(self, e):
        self.simulador.fijar_carga(float(e.control.value))
        self.al_cambiar()

    def _registrar_ordeno(self, e):
        ok, texto = self.simulador.registrar_ordeno()
        self.notificar(texto, ok)
        self.al_cambiar()

    # =============================================================
    # Validación y envío de comandos
    # =============================================================
    def _validar_umbral(self, e=None):
        """Revisa el campo en cada tecla: muestra el error y habilita el botón."""
        valor, error = validar_decimal(self.campo_umbral.value, config.UMBRAL_ACTIVIDAD_ALTA,
                                       config.UMBRAL_CELO_MAXIMO, "El umbral", incluir_minimo=False)
        self.campo_umbral.error = error
        self.boton_umbral.disabled = error is not None
        return valor

    def _enviar_umbral(self, e):
        valor = self._validar_umbral()
        if valor is None:
            self.notificar("Corrija el umbral antes de enviarlo", False)
            return
        self._enviar(config.TOPICO_CFG_UMBRAL, f"{valor:.2f}")

    def _validar_peso(self, e=None):
        valor, error = validar_decimal(self.campo_peso.value, 0.1, config.PESO_CALIBRACION_MAXIMO, "El peso")
        self.campo_peso.error = error
        self.boton_calibrar.disabled = error is not None
        return valor

    def _enviar_calibracion(self, e):
        valor = self._validar_peso()
        if valor is None:
            self.notificar("Escriba un peso válido antes de calibrar", False)
            return
        self._enviar(config.TOPICO_CMD_CALIBRAR, f"{valor:g}")

    def _enviar_intervalo(self, e):
        self._enviar(config.TOPICO_CFG_MUESTREO, e.control.value)

    def _enviar_tara(self, e):
        self._enviar(config.TOPICO_CMD_TARA, "1")

    def _enviar_buzzer(self, e):
        self._enviar(config.TOPICO_CMD_BUZZER, "silenciar" if e.control.value else "activar")

    def _enviar(self, topico, mensaje):
        """Envía el comando a la fuente de datos (hoy el simulador; luego MQTT)."""
        ok, texto = self.simulador.ejecutar_comando(topico, mensaje)
        self.notificar(texto, ok)
        self.al_cambiar()

    # =============================================================
    # Actualización periódica
    # =============================================================
    def actualizar(self, d):
        escenario = d["modo"] == config.MODO_ESCENARIO
        # El escenario puede terminar solo: se sincroniza el selector
        self.selector_modo.selected = [d["modo"]]
        self.panel_manual.visible = not escenario
        self.panel_escenario.visible = escenario
        self.linea_tiempo.actualizar(d["escenario"])

        comportamiento = d["comportamiento"]
        if comportamiento in config.COMPORTAMIENTOS:
            self.selector_comportamiento.selected = [comportamiento]
            self.texto_comportamiento.value = config.COMPORTAMIENTOS[comportamiento][2]
        else:
            self.selector_comportamiento.selected = []
            self.texto_comportamiento.value = f"Movimiento personalizado: {d['movimiento_simulado']:.3f} g"
        self.selector_reloj.value = str(d["velocidad"])
        # Los deslizadores reflejan el valor actual (también cuando lo cambia el escenario)
        self.deslizador_movimiento.value = round(d["movimiento_simulado"], 3)
        self.deslizador_carga.value = round(d["carga_objetivo"], 2)
        self.deslizador_movimiento.disabled = escenario
        self.deslizador_carga.disabled = escenario

        estado = "estable" if d["estable"] else "en movimiento"
        kg = d["kg"] if abs(d["kg"]) >= 0.005 else 0.0     # Evita mostrar "-0.00"
        self.texto_lectura.value = f"Lectura: {kg:.2f} kg  →  {d['litros']:.2f} L"
        self.texto_estabilidad.value = f"Peso {estado} · objetivo {d['carga_objetivo']:.1f} kg"

        self.interruptor_buzzer.value = d["buzzer_silenciado"]
