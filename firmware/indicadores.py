# indicadores.py
# Salidas visuales y sonoras del sistema:
#   - Semaforo: tres LEDs que muestran el estado de la vaca.
#   - Buzzer: alarma intermitente que NO bloquea el programa.

from machine import Pin, PWM
import time
import config


class Semaforo:
    """Tres LEDs (verde, amarillo, rojo). Solo uno encendido a la vez."""

    def __init__(self, pin_verde, pin_amarillo, pin_rojo):
        self.verde = Pin(pin_verde, Pin.OUT)
        self.amarillo = Pin(pin_amarillo, Pin.OUT)
        self.rojo = Pin(pin_rojo, Pin.OUT)
        self.apagar()

    def apagar(self):
        self.verde.off()
        self.amarillo.off()
        self.rojo.off()

    def mostrar(self, estado):
        """Enciende solo el LED que corresponde al estado recibido."""
        self.verde.value(1 if estado == config.ESTADO_NORMAL else 0)
        self.amarillo.value(1 if estado == config.ESTADO_ALTA else 0)
        self.rojo.value(1 if estado == config.ESTADO_CELO else 0)


class Buzzer:
    """Buzzer manejado con PWM, con sonido intermitente.

    No usa sleep(): guarda el momento del último cambio y, cada vez que se
    llama a actualizar(), revisa si ya pasó el intervalo para prender o
    apagar el tono. Así el resto del programa sigue funcionando.
    """

    def __init__(self, pin, frecuencia, intervalo_ms):
        self.pwm = PWM(Pin(pin), freq=frecuencia)
        self.pwm.duty_u16(0)            # Empieza en silencio
        self.intervalo = intervalo_ms
        self.activo = False             # ¿Hay una alarma activa?
        self.silenciado = False         # ¿El usuario la silenció?
        self.sonando = False            # ¿El tono está prendido en este instante?
        self.ultimo_cambio = time.ticks_ms()

    def _tono(self, encender):
        """Prende (50 % de ciclo útil) o apaga el tono."""
        self.sonando = encender
        self.pwm.duty_u16(32768 if encender else 0)

    def activar(self):
        self.activo = True

    def desactivar(self):
        """Termina la alarma. El silencio se reinicia para la próxima alerta."""
        self.activo = False
        self.silenciado = False
        self._tono(False)

    def silenciar(self, valor=True):
        """Silencia (True) o vuelve a permitir (False) la alarma actual."""
        self.silenciado = valor
        if valor:
            self._tono(False)

    def actualizar(self):
        """Debe llamarse en cada vuelta del bucle principal."""
        if not self.activo or self.silenciado:
            return
        ahora = time.ticks_ms()
        if time.ticks_diff(ahora, self.ultimo_cambio) >= self.intervalo:
            self.ultimo_cambio = ahora
            self._tono(not self.sonando)
