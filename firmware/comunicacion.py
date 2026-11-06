# comunicacion.py
# Conexión WiFi + MQTT con reconexión automática.
#
# Principio de diseño: el sistema funciona AUNQUE NO HAYA CONEXIÓN.
# LEDs, buzzer y balanza trabajan de forma local; el MQTT es una capa extra.
# Si la red se cae, se marca como desconectado y se reintenta cada cierto tiempo.

import network
import time
import json
import machine
import ubinascii
from umqtt.simple import MQTTClient


class ClienteMQTT:

    def __init__(self, ssid, clave, broker, puerto, cliente_id,
                 topico_conexion, topicos_comandos, al_recibir,
                 keepalive_s, ping_ms, reintento_ms, wifi_timeout_ms):
        self.ssid = ssid
        self.clave = clave
        self.topico_conexion = topico_conexion
        self.topicos_comandos = topicos_comandos
        self.al_recibir = al_recibir          # Función que procesa cada comando
        self.ping_ms = ping_ms
        self.reintento_ms = reintento_ms
        self.wifi_timeout_ms = wifi_timeout_ms

        # El ID debe ser único en el broker público: se le agrega el ID del chip
        id_chip = ubinascii.hexlify(machine.unique_id()).decode()
        self.cliente = MQTTClient(cliente_id + "_" + id_chip, broker,
                                  port=puerto, keepalive=keepalive_s)
        self.cliente.set_callback(self._mensaje_recibido)

        # Last Will: si la ESP32 se desconecta sin avisar, el BROKER publica
        # "desconectado" en su nombre. retain=True: la app lo ve aunque llegue tarde.
        self.cliente.set_last_will(topico_conexion, b"desconectado", retain=True)

        self.wlan = network.WLAN(network.STA_IF)
        self.conectado = False
        self.ultimo_intento = time.ticks_ms()
        self.ultimo_ping = time.ticks_ms()

    # ---------- Conexión ----------
    def _conectar_wifi(self):
        self.wlan.active(True)
        if self.wlan.isconnected():
            return True
        print("WiFi: conectando a", self.ssid, "...")
        self.wlan.connect(self.ssid, self.clave)
        inicio = time.ticks_ms()
        while not self.wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), inicio) > self.wifi_timeout_ms:
                print("WiFi: no se pudo conectar")
                return False
            time.sleep_ms(200)
        print("WiFi: conectado, IP", self.wlan.ifconfig()[0])
        return True

    def conectar(self):
        """Intenta conectar WiFi y MQTT. Devuelve True si lo logra."""
        self.ultimo_intento = time.ticks_ms()
        try:
            if not self._conectar_wifi():
                return False
            self.cliente.connect()
            for topico in self.topicos_comandos:
                self.cliente.subscribe(topico)
            self.cliente.publish(self.topico_conexion, b"conectado", retain=True)
            self.conectado = True
            self.ultimo_ping = time.ticks_ms()
            print("MQTT: conectado y suscrito a", len(self.topicos_comandos), "tópicos")
            return True
        except OSError as e:
            print("MQTT: error al conectar:", e)
            self.conectado = False
            return False

    # ---------- Envío y recepción ----------
    def publicar(self, topico, datos):
        """Envía un diccionario como JSON. Si falla, marca la desconexión."""
        if not self.conectado:
            return False
        try:
            self.cliente.publish(topico, json.dumps(datos))
            return True
        except OSError as e:
            print("MQTT: error al publicar:", e)
            self.conectado = False
            return False

    def _mensaje_recibido(self, topico, mensaje):
        """umqtt entrega bytes: se convierten a texto y se pasan al main."""
        try:
            self.al_recibir(topico.decode(), mensaje.decode().strip())
        except Exception as e:      # Un comando mal formado no debe tumbar el sistema
            print("Comando inválido:", e)

    def revisar(self):
        """Llamar en cada vuelta del bucle principal.

        - Conectado: revisa si llegaron comandos (sin esperar) y envía un ping.
        - Desconectado: reintenta cada 'reintento_ms'.
        """
        ahora = time.ticks_ms()
        if self.conectado:
            try:
                self.cliente.check_msg()        # No bloquea si no hay mensajes
                if time.ticks_diff(ahora, self.ultimo_ping) >= self.ping_ms:
                    self.cliente.ping()
                    self.ultimo_ping = ahora
            except OSError as e:
                print("MQTT: conexión perdida:", e)
                self.conectado = False
        elif time.ticks_diff(ahora, self.ultimo_intento) >= self.reintento_ms:
            self.conectar()
