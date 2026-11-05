# prueba_balanza.py  —  Prueba aislada del módulo de balanza.
# En Wokwi, pegar este contenido en main.py de una COPIA del proyecto.
# (El main.py del repositorio lo integra Jonathan.)
#
# - Al iniciar hace la tara (la balanza debe estar en 0 kg).
# - Cada 500 ms muestra kg, litros y si el peso es estable.
# - Al presionar el botón registra el ordeño, solo si el peso es estable.

import time
import config
from hx711 import HX711
from balanza import Balanza
from boton import Boton

sensor = HX711(config.PIN_HX711_DT, config.PIN_HX711_SCK)
balanza = Balanza(
    sensor,
    config.FACTOR_CALIBRACION,
    config.DENSIDAD_LECHE,
    config.MUESTRAS_ESTABILIDAD,
    config.TOLERANCIA_ESTABLE_KG,
)
boton = Boton(config.PIN_BOTON, config.ANTIRREBOTE_MS)

print("Haciendo tara... deja la balanza vacía")
balanza.tara()
print("Tara lista. Offset =", balanza.offset)

ultimo_print = time.ticks_ms()

while True:
    balanza.actualizar()

    ahora = time.ticks_ms()
    if time.ticks_diff(ahora, ultimo_print) >= config.INTERVALO_LECTURA_BALANZA_MS:
        ultimo_print = ahora
        estado = "estable" if balanza.es_estable() else "moviéndose"
        print("Peso: {:.2f} kg | {:.2f} L | {}".format(
            balanza.peso_kg(), balanza.litros(), estado))

    if boton.fue_presionado():
        if balanza.es_estable():
            print(">>> Ordeño registrado: {:.2f} L".format(balanza.litros()))
        else:
            print(">>> No se registró: el peso no está estable")

    time.sleep_ms(10)
