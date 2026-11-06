# main.py  —  ETAPA 4: sistema completo con comunicación MQTT.
#
# Bucle principal NO bloqueante: cada tarea se ejecuta cuando le toca.
#   Tarea 1: leer el MPU6050 cada 100 ms.
#   Tarea 2: leer la balanza cuando el HX711 tenga un dato listo.
#   Tarea 3: cada 10 s, evaluar la actividad, actualizar LEDs/buzzer y publicar.
#   Tarea 4: cada 2 s (ajustable por MQTT), publicar el peso de la leche.
#   Tarea 5: si se presiona el botón, registrar el ordeño y publicarlo.
#   Tarea 6: revisar comandos MQTT y reconectar si hace falta.
#   Tarea 7: mantener el sonido intermitente del buzzer.

import time
from machine import Pin, I2C
import config
from indicadores import Semaforo, Buzzer
from boton import Boton
from mpu6050 import MPU6050
from actividad import MonitorActividad
from hx711 import HX711
from balanza import Balanza
from comunicacion import ClienteMQTT

# ---------- Inicialización de hardware ----------
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

registros = []              # Litros de cada ordeño registrado
intervalo_publicacion = config.INTERVALO_PUBLICACION_MS


# ---------- Comandos recibidos desde la aplicación ----------
def procesar_comando(topico, mensaje):
    """Ejecuta la orden según el tópico por el que llegó."""
    global intervalo_publicacion
    print("Comando recibido:", topico, "=", mensaje)

    if topico == config.TOPICO_CFG_UMBRAL:
        valor = float(mensaje)
        if monitor.cambiar_umbral_celo(valor):
            print("Umbral de celo cambiado a", valor)
        else:
            print("Umbral rechazado: debe ser mayor que", monitor.umbral_alta)

    elif topico == config.TOPICO_CFG_MUESTREO:
        valor = int(mensaje)
        if valor >= 500:                    # Mínimo 0.5 s para no saturar el broker
            intervalo_publicacion = valor
            print("Intervalo de publicación:", valor, "ms")

    elif topico == config.TOPICO_CMD_TARA:
        balanza.tara()
        print("Tara realizada")

    elif topico == config.TOPICO_CMD_CALIBRAR:
        peso = float(mensaje)               # Peso conocido en kg sobre la balanza
        if balanza.calibrar(peso):
            print("Calibrada. Nuevo factor:", balanza.factor)
        else:
            print("Calibración inválida")

    elif topico == config.TOPICO_CMD_BUZZER:
        if mensaje.lower() == "silenciar":
            buzzer.silenciar(True)
        elif mensaje.lower() == "activar":
            buzzer.silenciar(False)
        print("Buzzer:", mensaje)


mqtt = ClienteMQTT(
    config.WIFI_SSID, config.WIFI_CLAVE,
    config.MQTT_BROKER, config.MQTT_PUERTO, config.MQTT_CLIENTE_ID,
    config.TOPICO_CONEXION,
    [config.TOPICO_CFG_UMBRAL, config.TOPICO_CFG_MUESTREO, config.TOPICO_CMD_TARA,
     config.TOPICO_CMD_CALIBRAR, config.TOPICO_CMD_BUZZER],
    procesar_comando,
    config.MQTT_KEEPALIVE_S, config.MQTT_PING_MS,
    config.MQTT_REINTENTO_MS, config.WIFI_TIMEOUT_MS,
)
mqtt.conectar()             # Si falla, el sistema sigue funcionando local

semaforo.mostrar(config.ESTADO_NORMAL)
segundos = config.VENTANA_ACTIVIDAD_MS * config.VENTANAS_CALIBRACION // 1000
print("Calibrando actividad durante", segundos, "s. Mantén el sensor quieto...")

ultima_lectura_mpu = time.ticks_ms()
ultima_publicacion_peso = time.ticks_ms()
monitor.inicio_ventana = time.ticks_ms()    # La ventana empieza tras conectar

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
            mqtt.publicar(config.TOPICO_ACTIVIDAD, {
                "actividad": round(monitor.actividad, 4),
                "linea_base": round(monitor.linea_base, 4),
                "razon": round(monitor.razon, 2),
            })
            mqtt.publicar(config.TOPICO_ESTADO, {
                "estado": monitor.estado,
                "umbral": monitor.umbral_celo,
            })

    # Tarea 4: publicación periódica del peso
    if time.ticks_diff(ahora, ultima_publicacion_peso) >= intervalo_publicacion:
        ultima_publicacion_peso = ahora
        estable = balanza.es_estable()
        print("[Leche] {:.2f} kg | {:.2f} L | {}".format(
            balanza.peso_kg(), balanza.litros(), "estable" if estable else "moviéndose"))
        mqtt.publicar(config.TOPICO_PESO, {
            "kg": round(balanza.peso_kg(), 2),
            "litros": round(balanza.litros(), 2),
            "estable": estable,
        })

    # Tarea 5: registrar el ordeño con el pulsador
    if boton.fue_presionado():
        if balanza.es_estable() and balanza.litros() > 0:
            litros = balanza.litros()
            registros.append(litros)
            print(">>> Ordeño #{} registrado: {:.2f} L | Total: {:.2f} L".format(
                len(registros), litros, sum(registros)))
            mqtt.publicar(config.TOPICO_REGISTRO, {
                "ordeno": len(registros),
                "litros": round(litros, 2),
                "total": round(sum(registros), 2),
            })
        else:
            print(">>> No se registró: el peso no está estable o la balanza está vacía")

    # Tarea 6: comandos entrantes y reconexión
    mqtt.revisar()

    # Tarea 7: buzzer intermitente
    buzzer.actualizar()

    time.sleep_ms(5)
