# hx711.py
# Driver mínimo del amplificador HX711 para celdas de carga.
#
# Cómo se comunica el HX711 (solo dos pines):
#   - DT  (datos, entrada en la ESP32): baja a 0 cuando hay una lectura lista.
#   - SCK (reloj, salida de la ESP32): por cada pulso, el HX711 entrega un bit.
# Se leen 24 bits (el valor) y se da 1 pulso extra (el 25) para que la
# siguiente lectura use el canal A con ganancia 128.

from machine import Pin
import machine


class HX711:

    def __init__(self, pin_dt, pin_sck):
        self.dt = Pin(pin_dt, Pin.IN)
        self.sck = Pin(pin_sck, Pin.OUT, value=0)   # SCK en 0 = sensor encendido

    def listo(self):
        """True si el HX711 tiene un dato nuevo (DT en 0)."""
        return self.dt.value() == 0

    def leer_crudo(self):
        """Lee el valor crudo de 24 bits con signo.

        Se debe llamar solo cuando listo() es True.
        """
        # Se desactivan las interrupciones mientras se leen los bits:
        # si SCK se queda en 1 más de 60 microsegundos, el HX711 se apaga.
        estado = machine.disable_irq()
        valor = 0
        for _ in range(24):
            self.sck.on()
            self.sck.off()
            valor = (valor << 1) | self.dt.value()   # Agrega el bit al final
        self.sck.on()                                # Pulso 25: canal A, ganancia 128
        self.sck.off()
        machine.enable_irq(estado)

        # El valor viene en complemento a dos: si el bit 23 es 1, es negativo
        if valor & 0x800000:
            valor -= 0x1000000
        return valor
