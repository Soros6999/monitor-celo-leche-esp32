# main.py  —  ETAPA 1: prueba de indicadores y botón.
# Cada pulsación pasa al siguiente estado:
#   NORMAL -> ACTIVIDAD ALTA -> CELO PROBABLE -> NORMAL ...
# En CELO PROBABLE el buzzer suena de forma intermitente.
# (Este main se reemplazará cuando se integren los sensores.)

import time
import config
from indicadores import Semaforo, Buzzer
from boton import Boton

semaforo = Semaforo(config.PIN_LED_VERDE, config.PIN_LED_AMARILLO, config.PIN_LED_ROJO)
buzzer = Buzzer(config.PIN_BUZZER, config.BUZZER_FRECUENCIA_HZ, config.BUZZER_INTERVALO_MS)
boton = Boton(config.PIN_BOTON, config.ANTIRREBOTE_MS)

estados = [config.ESTADO_NORMAL, config.ESTADO_ALTA, config.ESTADO_CELO]
indice = 0
semaforo.mostrar(estados[indice])
print("Prueba de indicadores. Estado:", estados[indice])

while True:
    if boton.fue_presionado():
        indice = (indice + 1) % len(estados)
        estado = estados[indice]
        semaforo.mostrar(estado)
        if estado == config.ESTADO_CELO:
            buzzer.activar()
        else:
            buzzer.desactivar()
        print("Estado:", estado)

    buzzer.actualizar()     # Hace sonar el buzzer sin bloquear
    time.sleep_ms(10)       # Pausa corta para no saturar el procesador
