# componentes/barra_estado.py
# Barra superior con la información general del sistema.
#
#   - Chips que se pueden pulsar (tienen borde e ícono de mano):
#       "Datos simulados" -> explica de dónde vienen los datos.
#       "ESP32 conectada" -> simula una caída de la conexión (caso real en campo).
#   - Chips solo informativos (sin borde): modo de la simulación y reloj.
#   - Tiempo simulado y hora actual.

from datetime import datetime

import flet as ft
import config
from componentes.tarjetas import Chip


class BarraEstado:

    def __init__(self, al_ver_origen, al_cambiar_conexion):
        self.chip_origen = Chip("Datos simulados", config.MORADO, ft.Icons.SCIENCE,
                                al_ver_origen, "¿De dónde vienen los datos?")
        self.chip_conexion = Chip("ESP32 conectada", config.VERDE, None,
                                  al_cambiar_conexion, "Clic: simular que se cae o vuelve la conexión")
        self.chip_modo = Chip("Simulación manual", config.TEXTO_SEC, ft.Icons.TUNE)
        self.chip_reloj = Chip("Reloj ×1", config.AMARILLO, ft.Icons.FAST_FORWARD)
        self.texto_marcha = ft.Text("", size=12, color=config.TEXTO_SEC)
        self.texto_hora = ft.Text("", size=13, color=config.TEXTO, weight=ft.FontWeight.W_600)
        # Dos grupos: chips a la izquierda y reloj a la derecha.
        # wrap=True hace que en el celular pasen a una segunda línea.
        self.control = ft.Row(
            wrap=True, spacing=8, run_spacing=8,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Row(wrap=True, tight=True, spacing=8, run_spacing=8, controls=[
                    self.chip_origen.control, self.chip_conexion.control,
                    self.chip_modo.control, self.chip_reloj.control,
                ]),
                ft.Row(tight=True, spacing=12, controls=[self.texto_marcha, self.texto_hora]),
            ],
        )

    def actualizar(self, d):
        if d["conectado"]:
            self.chip_conexion.actualizar("ESP32 conectada", config.VERDE)
        else:
            self.chip_conexion.actualizar("ESP32 desconectada", config.ROJO)

        if d["modo"] == config.MODO_ESCENARIO:
            self.chip_modo.icono.icon = ft.Icons.SMART_DISPLAY
            self.chip_modo.actualizar("Simulación: escenario", config.ACENTO)
        else:
            self.chip_modo.icono.icon = ft.Icons.TUNE
            self.chip_modo.actualizar("Simulación: manual", config.TEXTO_SEC)

        # El reloj solo se muestra cuando está acelerado, para que no pase inadvertido
        self.chip_reloj.control.visible = d["velocidad"] != 1
        self.chip_reloj.actualizar(f"Reloj acelerado ×{d['velocidad']}", config.AMARILLO)

        segundos = int(d["tiempo"])
        self.texto_marcha.value = f"Tiempo simulado {segundos // 60:02d}:{segundos % 60:02d}"
        self.texto_hora.value = datetime.now().strftime("%H:%M:%S")
