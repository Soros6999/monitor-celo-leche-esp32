# main.py  —  ETAPA 2: detección de actividad con el MPU6050.
# Lee el acelerómetro cada 100 ms, calcula la actividad cada 10 s
# y muestra el estado de la vaca con los LEDs y el buzzer.

import time
from machine import Pin, I2C
import config
from indicadores import Semaforo, Buzzer
from mpu6050 import MPU6050
from actividad import MonitorActividad

# ---------- Inicialización ----------
semaforo = Semaforo(config.PIN_LED_VERDE, config.PIN_LED_AMARILLO, config.PIN_LED_ROJO)
buzzer = Buzzer(config.PIN_BUZZER, config.BUZZER_FRECUENCIA_HZ, config.BUZZER_INTERVALO_MS)

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

semaforo.mostrar(config.ESTADO_NORMAL)
segundos = config.VENTANA_ACTIVIDAD_MS * config.VENTANAS_CALIBRACION // 1000
print("Calibrando línea base durante", segundos, "s. Mantén el sensor quieto...")

ultima_lectura_mpu = time.ticks_ms()

# ---------- Bucle principal ----------
while True:
    ahora = time.ticks_ms()

    # Tarea 1: leer el acelerómetro cada INTERVALO_LECTURA_MPU_MS
    if time.ticks_diff(ahora, ultima_lectura_mpu) >= config.INTERVALO_LECTURA_MPU_MS:
        ultima_lectura_mpu = ahora
        try:
            ax, ay, az = mpu.leer_aceleracion()
            monitor.agregar_muestra(ax, ay, az)
        except OSError as e:
            print("Error leyendo el MPU6050:", e)

    # Tarea 2: cuando termina una ventana, actualizar estado y salidas
    if monitor.actualizar():
        if monitor.calibrando:
            print("Calibrando... ventana", monitor.ventanas_calibradas,
                  "de", config.VENTANAS_CALIBRACION)
        else:
            print("Actividad: {:.4f} g | Base: {:.4f} g | Razón: {:.2f} | {}".format(
                monitor.actividad, monitor.linea_base, monitor.razon, monitor.estado))
            semaforo.mostrar(monitor.estado)
            if monitor.estado == config.ESTADO_CELO:
                buzzer.activar()
            else:
                buzzer.desactivar()

    # Tarea 3: mantener el sonido intermitente del buzzer
    buzzer.actualizar()

    time.sleep_ms(5)
