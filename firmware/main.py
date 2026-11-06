# main.py  —  ETAPA 3: sistema completo local (celo + balanza + pulsador).
#
# Bucle principal NO bloqueante: cada tarea se ejecuta cuando le toca,
# comparando el tiempo actual con la última vez que se hizo.
#   Tarea 1: leer el MPU6050 cada 100 ms.
#   Tarea 2: leer la balanza cuando el HX711 tenga un dato listo.
#   Tarea 3: cada 10 s, evaluar la actividad y actualizar LEDs y buzzer.
#   Tarea 4: cada 2 s, mostrar el peso de la leche.
#   Tarea 5: si se presiona el botón, registrar el ordeño (si el peso es estable).
#   Tarea 6: mantener el sonido intermitente del buzzer.

import time
from machine import Pin, I2C
import config
from indicadores import Semaforo, Buzzer
from boton import Boton
from mpu6050 import MPU6050
from actividad import MonitorActividad
from hx711 import HX711
from balanza import Balanza

# ---------- Inicialización ----------
semaforo = Semaforo(config.PIN_LED_VERDE, config.PIN_LED_AMARILLO, config.PIN_LED_ROJO)
buzzer = Buzzer(config.PIN_BUZZER, config.BUZZER_FRECUENCIA_HZ, config.BUZZER_INTERVALO_MS)
boton = Boton(config.PIN_BOTON, config.ANTIRREBOTE_MS)

i2c = I2C(0, sda=Pin(config.PIN_I2C_SDA), scl=Pin(config.PIN_I2C_SCL), freq=400000)
mpu = MPU6050(i2c)
monitor = MonitorActividad(
    config.VENTANA_ACTIVIDAD_MS,
    config.VENTANAS_CALIBRACION,
    config.ALFA_LINEA_BASE,
    config.UMBRAL_ACTIVIDAD_ALTA,
    config.UMBRAL_CELO,
    config.LINEA_BASE_MINIMA,
)

balanza = Balanza(
    HX711(config.PIN_HX711_DT, config.PIN_HX711_SCK),
    config.FACTOR_CALIBRACION,
    config.DENSIDAD_LECHE,
    config.MUESTRAS_ESTABILIDAD,
    config.TOLERANCIA_ESTABLE_KG,
)
try:
    balanza.tara()          # La balanza debe estar vacía al encender
    print("Balanza: tara lista")
except OSError as e:
    print("Balanza: error en la tara:", e)

registros = []              # Litros de cada ordeño registrado (en memoria)

semaforo.mostrar(config.ESTADO_NORMAL)
segundos = config.VENTANA_ACTIVIDAD_MS * config.VENTANAS_CALIBRACION // 1000
print("Calibrando actividad durante", segundos, "s. Mantén el sensor quieto...")

ultima_lectura_mpu = time.ticks_ms()
ultimo_reporte_balanza = time.ticks_ms()

# ---------- Bucle principal ----------
while True:
    ahora = time.ticks_ms()

    # Tarea 1: acelerómetro
    if time.ticks_diff(ahora, ultima_lectura_mpu) >= config.INTERVALO_LECTURA_MPU_MS:
        ultima_lectura_mpu = ahora
        try:
            ax, ay, az = mpu.leer_aceleracion()
            monitor.agregar_muestra(ax, ay, az)
        except OSError as e:
            print("Error leyendo el MPU6050:", e)

    # Tarea 2: balanza (no espera: si no hay dato listo, sigue de largo)
    balanza.actualizar()

    # Tarea 3: estado de la vaca al cerrar cada ventana de actividad
    if monitor.actualizar():
        if monitor.calibrando:
            print("Calibrando... ventana", monitor.ventanas_calibradas,
                  "de", config.VENTANAS_CALIBRACION)
        else:
            print("[Vaca] Actividad: {:.4f} g | Base: {:.4f} g | Razón: {:.2f} | {}".format(
                monitor.actividad, monitor.linea_base, monitor.razon, monitor.estado))
            semaforo.mostrar(monitor.estado)
            if monitor.estado == config.ESTADO_CELO:
                buzzer.activar()
            else:
                buzzer.desactivar()

    # Tarea 4: reporte periódico de la balanza
    if time.ticks_diff(ahora, ultimo_reporte_balanza) >= config.INTERVALO_PUBLICACION_MS:
        ultimo_reporte_balanza = ahora
        estado_peso = "estable" if balanza.es_estable() else "moviéndose"
        print("[Leche] {:.2f} kg | {:.2f} L | {}".format(
            balanza.peso_kg(), balanza.litros(), estado_peso))

    # Tarea 5: registrar el ordeño con el pulsador
    if boton.fue_presionado():
        if balanza.es_estable() and balanza.litros() > 0:
            litros = balanza.litros()
            registros.append(litros)
            print(">>> Ordeño #{} registrado: {:.2f} L | Total: {:.2f} L".format(
                len(registros), litros, sum(registros)))
        else:
            print(">>> No se registró: el peso no está estable o la balanza está vacía")

    # Tarea 6: buzzer intermitente
    buzzer.actualizar()

    time.sleep_ms(5)
