# config.py
# Configuración central del firmware.
# Todos los valores que se pueden ajustar (pines, tiempos, umbrales, red)
# están aquí, para que cambiar el comportamiento sea editar SOLO este archivo.

# ---------------------------------------------------------------
# PINES (ESP32)
# Se evitan los pines 34-39 (solo entrada) y los pines de arranque
# (0, 2, 12, 15), que pueden impedir que la placa inicie.
# ---------------------------------------------------------------
PIN_I2C_SDA = 21        # MPU6050 (y OLED opcional) comparten el bus I2C
PIN_I2C_SCL = 22

PIN_HX711_DT = 4        # Datos de la balanza
PIN_HX711_SCK = 5       # Reloj de la balanza

PIN_LED_VERDE = 25
PIN_LED_AMARILLO = 26
PIN_LED_ROJO = 27

PIN_BUZZER = 14         # Se maneja con PWM para generar el tono
PIN_BOTON = 13          # Con resistencia pull-up interna (presionado = 0)

# ---------------------------------------------------------------
# ESTADOS DE LA VACA
# ---------------------------------------------------------------
ESTADO_NORMAL = "NORMAL"
ESTADO_ALTA = "ACTIVIDAD_ALTA"
ESTADO_CELO = "CELO_PROBABLE"

# ---------------------------------------------------------------
# BUZZER
# ---------------------------------------------------------------
BUZZER_FRECUENCIA_HZ = 2000         # Tono del buzzer
BUZZER_INTERVALO_MS = 300           # Sonido intermitente: 300 ms on / 300 ms off

# ---------------------------------------------------------------
# ACTIVIDAD (detección de posible celo)
# ---------------------------------------------------------------
INTERVALO_LECTURA_MPU_MS = 100      # Leer el acelerómetro cada 100 ms (10 Hz)
VENTANA_ACTIVIDAD_MS = 10000        # Sumar actividad durante 10 s
VENTANAS_CALIBRACION = 3            # Ventanas iniciales para calcular lo "normal"
ALFA_LINEA_BASE = 0.1               # Qué tan rápido se adapta la línea base (0-1)

UMBRAL_ACTIVIDAD_ALTA = 1.5         # razón >= 1.5 -> LED amarillo
UMBRAL_CELO = 2.0                   # razón >= 2.0 -> LED rojo + buzzer + alerta

# ---------------------------------------------------------------
# BALANZA
# ---------------------------------------------------------------
INTERVALO_LECTURA_BALANZA_MS = 500
DENSIDAD_LECHE = 1.03               # kg por litro
FACTOR_CALIBRACION = 420.0          # Lecturas crudas por kg (se ajusta al calibrar)
MUESTRAS_ESTABILIDAD = 5            # Lecturas que se comparan
TOLERANCIA_ESTABLE_KG = 0.02        # Estable si varían menos de 20 g

# ---------------------------------------------------------------
# BOTÓN
# ---------------------------------------------------------------
ANTIRREBOTE_MS = 50

# ---------------------------------------------------------------
# RED Y MQTT
# ---------------------------------------------------------------
WIFI_SSID = "Wokwi-GUEST"           # Red del simulador (sin contraseña)
WIFI_CLAVE = ""

MQTT_BROKER = "test.mosquitto.org"  # Broker público (Wokwi no ve un broker local)
MQTT_PUERTO = 1883
MQTT_CLIENTE_ID = "esp32_vaca01_utp"
INTERVALO_PUBLICACION_MS = 2000     # Cada cuánto se envían datos

# Prefijo único para no mezclarse con otros usuarios del broker público
PREFIJO = "utp_prog2_rt"

# Tópicos ESP32 -> App
TOPICO_ACTIVIDAD = PREFIJO + "/celo/vaca01/actividad"
TOPICO_ESTADO = PREFIJO + "/celo/vaca01/estado"
TOPICO_PESO = PREFIJO + "/leche/balanza/peso"
TOPICO_REGISTRO = PREFIJO + "/leche/balanza/registro"
TOPICO_CONEXION = PREFIJO + "/sistema/esp32/conexion"

# Tópicos App -> ESP32
TOPICO_CFG_UMBRAL = PREFIJO + "/celo/vaca01/config/umbral"
TOPICO_CFG_MUESTREO = PREFIJO + "/celo/vaca01/config/muestreo"
TOPICO_CMD_TARA = PREFIJO + "/leche/balanza/cmd/tara"
TOPICO_CMD_CALIBRAR = PREFIJO + "/leche/balanza/cmd/calibrar"
TOPICO_CMD_BUZZER = PREFIJO + "/sistema/esp32/cmd/buzzer"
