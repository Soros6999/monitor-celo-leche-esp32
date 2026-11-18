# config.py
# Configuración central de la interfaz gráfica.
# Igual que en el firmware: todo lo que se puede ajustar (colores, tamaños,
# tiempos, umbrales) vive aquí, para que un cambio sea editar una sola línea.

# ---------------------------------------------------------------
# VENTANA
# ---------------------------------------------------------------
TITULO_APP = "Monitor de celo y leche"
SUBTITULO_APP = "Vaca 01 · Prototipo ESP32"
ANCHO_VENTANA = 1280
ALTO_VENTANA = 800
ANCHO_MINIMO = 380        # Permite verla en formato celular
ALTO_MINIMO = 600
ANCHO_MODO_MOVIL = 760    # Por debajo de este ancho se usa la barra inferior

# ---------------------------------------------------------------
# COLORES (tema oscuro)
# ---------------------------------------------------------------
FONDO = "#0E1620"
PANEL = "#16212D"
PANEL_2 = "#22303F"
BORDE = "#2C3B4C"
TEXTO = "#EAF1F7"
TEXTO_SEC = "#8EA2B5"
ACENTO = "#3FC1A5"        # Verde menta: color propio de la aplicación

# Colores con significado (los mismos del semáforo del firmware)
VERDE = "#35C77A"         # NORMAL
AMARILLO = "#F2B33D"      # ACTIVIDAD ALTA
ROJO = "#EF5350"          # CELO PROBABLE / alarma
AZUL = "#4FA3F7"          # Leche
MORADO = "#A98BF0"        # MQTT / comunicación

# ---------------------------------------------------------------
# ESTADOS DE LA VACA (mismos textos que publica el firmware)
# ---------------------------------------------------------------
ESTADO_NORMAL = "NORMAL"
ESTADO_ALTA = "ACTIVIDAD_ALTA"
ESTADO_CELO = "CELO_PROBABLE"
ESTADO_CALIBRANDO = "CALIBRANDO"

# Texto y color con que se muestra cada estado
NOMBRE_ESTADO = {
    ESTADO_NORMAL: "Normal",
    ESTADO_ALTA: "Actividad alta",
    ESTADO_CELO: "Posible celo",
    ESTADO_CALIBRANDO: "Calibrando",
}
COLOR_ESTADO = {
    ESTADO_NORMAL: VERDE,
    ESTADO_ALTA: AMARILLO,
    ESTADO_CELO: ROJO,
    ESTADO_CALIBRANDO: TEXTO_SEC,
}

# ---------------------------------------------------------------
# ACTUALIZACIÓN PERIÓDICA
# ---------------------------------------------------------------
PERIODO_ACTUALIZACION_S = 0.5     # La interfaz se refresca 2 veces por segundo
VELOCIDADES = [1, 2, 5, 10]       # Multiplicadores del RELOJ de la simulación

# ---------------------------------------------------------------
# SIMULACIÓN
# ---------------------------------------------------------------
MODO_MANUAL = "manual"
MODO_ESCENARIO = "escenario"

# Comportamientos de la vaca: (nombre visible, movimiento extra en g, descripción)
COMPORTAMIENTOS = {
    "reposo": ("Reposo", 0.06, "Pastando o echada: movimiento normal"),
    "inquieta": ("Inquieta", 0.105, "Se mueve más de lo normal"),
    "celo": ("En celo", 0.20, "Monta, camina y se agita mucho más"),
}
MOVIMIENTO_MAXIMO = 0.30          # Tope del deslizador de ajuste fino (g)

# Escenario de demostración: se ejecuta UNA vez, fase por fase.
# (nombre, comportamiento, duración en segundos simulados, descripción)
ESCENARIO = [
    ("Calibración y reposo", "reposo", 60, "El sistema aprende lo normal (30 s) y la vaca sigue tranquila"),
    ("Inquieta", "inquieta", 40, "La vaca se mueve más: debería pasar a Actividad alta"),
    ("Posible celo", "celo", 60, "Movimiento muy alto: alarma de posible celo"),
    ("Recuperación", "reposo", 50, "Vuelve la calma: el estado regresa a Normal"),
]

# ---------------------------------------------------------------
# LÓGICA DE ACTIVIDAD (mismos valores que firmware/config.py)
# ---------------------------------------------------------------
INTERVALO_MUESTRA_S = 0.1         # El MPU6050 se lee cada 100 ms
VENTANA_ACTIVIDAD_S = 10          # Ventana de 10 s
VENTANAS_CALIBRACION = 3          # 30 s de calibración
ALFA_LINEA_BASE = 0.1
LINEA_BASE_MINIMA = 0.02          # g
UMBRAL_ACTIVIDAD_ALTA = 1.5
UMBRAL_CELO = 2.0
UMBRAL_CELO_MAXIMO = 5.0          # Límite superior aceptado al validar
# Histéresis: para BAJAR de estado la razón debe quedar este margen por
# debajo del umbral. Evita que el estado salte de un lado a otro cuando la
# razón está justo en el límite (p. ej. entra a ALTA con 1.5, sale con 1.3).
MARGEN_HISTERESIS = 0.2
VENTANAS_EN_GRAFICA = 30          # Ventanas que se dibujan (5 minutos)
MUESTRAS_EN_GRAFICA = 100         # Muestras instantáneas que se dibujan (10 s)

# ---------------------------------------------------------------
# BALANZA (mismos valores que firmware/config.py)
# ---------------------------------------------------------------
DENSIDAD_LECHE = 1.03             # kg por litro
FACTOR_CALIBRACION = 420.0        # Lecturas crudas por kg (celda de 50 kg de Wokwi)
MUESTRAS_ESTABILIDAD = 5
TOLERANCIA_ESTABLE_KG = 0.02
CAPACIDAD_BALDE_KG = 20.0         # Para dibujar el nivel del balde
PESO_CALIBRACION_MAXIMO = 50.0    # kg: capacidad de la celda

# ---------------------------------------------------------------
# PUBLICACIÓN
# ---------------------------------------------------------------
INTERVALO_PUBLICACION_MS = 2000
INTERVALOS_PUBLICACION_MS = [1000, 2000, 5000, 10000]

# ---------------------------------------------------------------
# TÓPICOS MQTT (los mismos del firmware). Hoy los usa el simulador;
# en la integración final los usará el cliente MQTT real.
# ---------------------------------------------------------------
PREFIJO = "utp_prog2_rt"
TOPICO_ACTIVIDAD = PREFIJO + "/celo/vaca01/actividad"
TOPICO_ESTADO = PREFIJO + "/celo/vaca01/estado"
TOPICO_PESO = PREFIJO + "/leche/balanza/peso"
TOPICO_REGISTRO = PREFIJO + "/leche/balanza/registro"
TOPICO_CONEXION = PREFIJO + "/sistema/esp32/conexion"
TOPICO_CFG_UMBRAL = PREFIJO + "/celo/vaca01/config/umbral"
TOPICO_CFG_MUESTREO = PREFIJO + "/celo/vaca01/config/muestreo"
TOPICO_CMD_TARA = PREFIJO + "/leche/balanza/cmd/tara"
TOPICO_CMD_CALIBRAR = PREFIJO + "/leche/balanza/cmd/calibrar"
TOPICO_CMD_BUZZER = PREFIJO + "/sistema/esp32/cmd/buzzer"
MENSAJES_GUARDADOS = 60           # Últimos mensajes MQTT que se conservan

# ---------------------------------------------------------------
# EVENTOS
# ---------------------------------------------------------------
EVENTO_ALERTA = "Alerta"
EVENTO_COMANDO = "Comando"
EVENTO_ORDENO = "Ordeño"
EVENTO_CONEXION = "Conexión"
EVENTO_SISTEMA = "Sistema"
TIPOS_EVENTO = [EVENTO_ALERTA, EVENTO_COMANDO, EVENTO_ORDENO, EVENTO_CONEXION, EVENTO_SISTEMA]
EVENTOS_GUARDADOS = 200
