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
