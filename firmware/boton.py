# boton.py
# Pulsador con resistencia pull-up interna y antirrebote por software.

from machine import Pin
import time


class Boton:
    """Detecta pulsaciones de un botón conectado entre el pin y GND.

    Pull-up interna: sin presionar el pin lee 1; presionado lee 0.
    Antirrebote: un pulsador mecánico "rebota" (cambia varias veces en pocos
    milisegundos). Solo se acepta un cambio si la lectura se mantiene igual
    durante 'antirrebote_ms'.
    """

    def __init__(self, pin, antirrebote_ms):
        self.pin = Pin(pin, Pin.IN, Pin.PULL_UP)
        self.antirrebote = antirrebote_ms
        self.estado_estable = self.pin.value()   # Último valor confirmado
        self.ultima_lectura = self.estado_estable
        self.tiempo_cambio = time.ticks_ms()

    def fue_presionado(self):
        """Devuelve True UNA sola vez por cada pulsación."""
        lectura = self.pin.value()
        ahora = time.ticks_ms()

        # Si la lectura cambió, se reinicia el conteo del antirrebote
        if lectura != self.ultima_lectura:
            self.ultima_lectura = lectura
            self.tiempo_cambio = ahora
            return False

        # Si la lectura se mantuvo estable el tiempo suficiente, se acepta
        if (lectura != self.estado_estable and
                time.ticks_diff(ahora, self.tiempo_cambio) >= self.antirrebote):
            self.estado_estable = lectura
            return lectura == 0     # Solo cuenta el momento de presionar

        return False
