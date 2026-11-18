# modelo/simulador.py
# Simulador del sistema completo: reemplaza a la ESP32 mientras no hay integración.
#
# Hace lo mismo que el firmware:
#   - genera lecturas del acelerómetro y de la balanza,
#   - las procesa con MonitorActividad y BalanzaSimulada (misma lógica),
#   - "publica" los mismos mensajes JSON en los mismos tópicos MQTT,
#   - y obedece los mismos 5 comandos.
#
# Tiene dos modos:
#   - MANUAL: el usuario elige el comportamiento de la vaca y la carga del
#     balde; se mantienen hasta que él los cambie.
#   - ESCENARIO: una demostración de 4 fases que se ejecuta UNA sola vez.
#
# Las vistas solo usan estado() y ejecutar_comando(). En la integración
# final este simulador se cambia por un cliente MQTT real sin tocar las pantallas.

import json
import math
import random
from datetime import datetime, timedelta

import config
from modelo.actividad import MonitorActividad
from modelo.balanza import BalanzaSimulada


class Evento:
    """Un suceso del sistema con su fecha, tipo y descripción."""

    def __init__(self, tipo, mensaje, fecha=None):
        self.fecha = fecha or datetime.now()
        self.tipo = tipo
        self.mensaje = mensaje


class SimuladorSistema:

    def __init__(self):
        self.monitor = MonitorActividad(
            config.VENTANA_ACTIVIDAD_S, config.VENTANAS_CALIBRACION,
            config.ALFA_LINEA_BASE, config.UMBRAL_ACTIVIDAD_ALTA,
            config.UMBRAL_CELO, config.LINEA_BASE_MINIMA, config.MARGEN_HISTERESIS,
        )
        self.balanza = BalanzaSimulada(
            config.FACTOR_CALIBRACION, config.DENSIDAD_LECHE,
            config.MUESTRAS_ESTABILIDAD, config.TOLERANCIA_ESTABLE_KG,
        )

        self.tiempo = 0.0                 # Segundos simulados desde el arranque
        self.velocidad = 1                # Multiplicador del RELOJ (no del movimiento)
        self.conectado = True
        self.buzzer_silenciado = False
        self.intervalo_publicacion_ms = config.INTERVALO_PUBLICACION_MS
        self._acumulado_publicacion = 0.0
        self._acumulado_muestra = 0.0

        # Comportamiento de la vaca
        self.modo = config.MODO_MANUAL
        self.comportamiento = "reposo"
        self.movimiento = config.COMPORTAMIENTOS["reposo"][1]   # g extra

        # Movimientos espontáneos (picos cortos y variación lenta)
        self.espontaneos = False
        self._pico_restante = 0.0
        self._pico_intensidad = 0.0
        self.picos = 0                    # Cuántos picos han ocurrido

        # Escenario
        self.tiempo_escenario = 0.0
        self.fase = 0
        self._ordeno_escenario = False

        self.movimientos = []             # Últimas muestras instantáneas (gráfica)
        self.lecturas_kg = []             # Últimas lecturas de la balanza (gráfica de estabilidad)
        self.registros = []               # Ordeños: lista de diccionarios
        self.eventos = []                 # Lista de Evento
        self.mensajes = []                # Últimos mensajes "publicados" por MQTT

        self._cargar_ordenos_de_ejemplo()
        self.registrar_evento(config.EVENTO_SISTEMA, "Sistema iniciado con datos simulados")
        self.registrar_evento(config.EVENTO_CONEXION, "Conectado al broker (simulado)")
        self._publicar(config.TOPICO_CONEXION, "conectado")

    # =============================================================
    # Avance del tiempo
    # =============================================================
    def avanzar(self, dt_real):
        """Avanza la simulación dt_real segundos multiplicados por la velocidad
        del reloj. Se divide en pasos de 100 ms, igual que el firmware lee el
        MPU6050 cada 100 ms."""
        self._acumulado_muestra += dt_real * self.velocidad
        while self._acumulado_muestra >= config.INTERVALO_MUESTRA_S - 1e-9:
            self._acumulado_muestra -= config.INTERVALO_MUESTRA_S
            self._paso(config.INTERVALO_MUESTRA_S)

    def _paso(self, dt):
        self.tiempo += dt
        if self.modo == config.MODO_ESCENARIO:
            self._avanzar_escenario(dt)

        self._actualizar_picos(dt)

        # Tarea 1 del firmware: leer el acelerómetro
        ax, ay, az = self._leer_acelerometro()
        self.monitor.agregar_muestra(ax, ay, az)
        self.movimientos.append(self.monitor.ultimo_movimiento)
        if len(self.movimientos) > config.MUESTRAS_EN_GRAFICA:
            self.movimientos.pop(0)

        # Tarea 2: leer la balanza
        self.balanza.actualizar()
        self.lecturas_kg.append(self.balanza.lecturas[-1])
        if len(self.lecturas_kg) > config.LECTURAS_EN_GRAFICA:
            self.lecturas_kg.pop(0)

        # Tarea 3: al cerrar la ventana, evaluar el estado y publicar
        estado_anterior = self.monitor.estado
        if self.monitor.avanzar(dt):
            self._al_cerrar_ventana(estado_anterior)

        # Tarea 4: publicar el peso cada intervalo
        self._acumulado_publicacion += dt * 1000
        if self._acumulado_publicacion >= self.intervalo_publicacion_ms:
            self._acumulado_publicacion = 0.0
            self._publicar(config.TOPICO_PESO, {
                "kg": round(self.balanza.peso_kg(), 2) + 0.0,     # + 0.0 evita "-0.0"
                "litros": round(self.balanza.litros(), 2) + 0.0,
                "estable": self.balanza.es_estable(),
            })

    def _al_cerrar_ventana(self, estado_anterior):
        m = self.monitor
        if m.calibrando:
            return
        self._publicar(config.TOPICO_ACTIVIDAD, {
            "actividad": round(m.actividad, 4),
            "linea_base": round(m.linea_base, 4),
            "razon": round(m.razon, 2),
        })
        self._publicar(config.TOPICO_ESTADO, {"estado": m.estado, "umbral": m.umbral_celo})

        if estado_anterior == config.ESTADO_CALIBRANDO:
            self.registrar_evento(config.EVENTO_SISTEMA,
                                  f"Línea base calibrada: {m.linea_base:.4f} g")
        elif m.estado != estado_anterior:
            nombre = config.NOMBRE_ESTADO[m.estado]
            tipo = config.EVENTO_ALERTA if m.estado != config.ESTADO_NORMAL else config.EVENTO_SISTEMA
            self.registrar_evento(tipo, f"Estado de la vaca: {nombre} (razón {m.razon:.2f})")
        # La alarma vuelve a sonar en un nuevo episodio de celo
        if m.estado != config.ESTADO_CELO:
            self.buzzer_silenciado = False

    # =============================================================
    # Sensor simulado
    # =============================================================
    def _leer_acelerometro(self):
        """Gravedad (0, 0, 1 g) más un movimiento aleatorio de la intensidad actual.

        Al caminar, el collar se mueve sobre todo de arriba abajo; por eso el
        movimiento va casi vertical (inclinación entre 0.7 y 1) y su tamaño
        varía alrededor de la intensidad elegida (entre 40 % y 160 %).
        """
        extra = self._movimiento_efectivo() * random.uniform(0.4, 1.6)
        angulo = random.uniform(0, 2 * math.pi)
        inclinacion = random.choice((-1, 1)) * random.uniform(0.7, 1.0)
        horizontal = math.sqrt(1 - inclinacion ** 2)
        ax = extra * math.cos(angulo) * horizontal
        ay = extra * math.sin(angulo) * horizontal
        az = 1.0 + extra * inclinacion
        return ax, ay, az

    def _movimiento_efectivo(self):
        """Movimiento base, con variación lenta y picos si están activados."""
        if self._pico_restante > 0:
            return self._pico_intensidad
        if self.espontaneos:
            return self.movimiento * (1 + config.VARIACION_LENTA * math.sin(self.tiempo / 37))
        return self.movimiento

    def _actualizar_picos(self, dt):
        if self._pico_restante > 0:
            self._pico_restante -= dt
            return
        if self.espontaneos and random.random() < config.PROBABILIDAD_PICO:
            self.provocar_pico()

    def provocar_pico(self, duracion=None, intensidad=None):
        """Un movimiento brusco y corto: un susto, un empujón, una carrera breve."""
        self._pico_restante = duracion or random.uniform(*config.DURACION_PICO_S)
        self._pico_intensidad = intensidad or random.uniform(*config.INTENSIDAD_PICO_G)
        self.picos += 1

    # =============================================================
    # Modo manual
    # =============================================================
    def fijar_comportamiento(self, clave):
        """Reposo / Inquieta / En celo. Se mantiene hasta que se cambie."""
        self.comportamiento = clave
        self.movimiento = config.COMPORTAMIENTOS[clave][1]
        nombre = config.COMPORTAMIENTOS[clave][0]
        self.registrar_evento(config.EVENTO_SISTEMA, f"Simulación: la vaca pasa a «{nombre}»")

    def fijar_movimiento(self, g):
        """Ajuste fino del movimiento (deslizador)."""
        self.movimiento = max(0.0, min(g, config.MOVIMIENTO_MAXIMO))
        self.comportamiento = "personalizado"

    def fijar_carga(self, kg):
        self.balanza.fijar_carga(kg)

    def cambiar_espontaneos(self, activo):
        self.espontaneos = activo
        texto = "activados" if activo else "desactivados"
        self.registrar_evento(config.EVENTO_SISTEMA, f"Movimientos espontáneos {texto}")

    def cambiar_velocidad(self, velocidad):
        self.velocidad = velocidad
        self.registrar_evento(config.EVENTO_SISTEMA, f"Reloj de la simulación: ×{velocidad}")

    # =============================================================
    # Escenario de demostración
    # =============================================================
    def iniciar_escenario(self):
        self.modo = config.MODO_ESCENARIO
        self.tiempo_escenario = 0.0
        self.fase = 0
        self._ordeno_escenario = False
        self._aplicar_fase()
        self.registrar_evento(config.EVENTO_SISTEMA, "Escenario de demostración iniciado")

    def detener_escenario(self, terminado=False):
        self.modo = config.MODO_MANUAL
        self.fijar_comportamiento("reposo")
        self.balanza.fijar_carga(0)
        texto = "Escenario de demostración terminado" if terminado else "Escenario detenido: modo manual"
        self.registrar_evento(config.EVENTO_SISTEMA, texto)

    def _aplicar_fase(self):
        clave = config.ESCENARIO[self.fase][1]
        self.comportamiento = clave
        self.movimiento = config.COMPORTAMIENTOS[clave][1]

    def _avanzar_escenario(self, dt):
        self.tiempo_escenario += dt
        # ¿Terminó la fase actual?
        fin_fase = sum(f[2] for f in config.ESCENARIO[:self.fase + 1])
        if self.tiempo_escenario >= fin_fase:
            if self.fase + 1 >= len(config.ESCENARIO):
                self.detener_escenario(terminado=True)
                return
            self.fase += 1
            self._aplicar_fase()
            self.registrar_evento(config.EVENTO_SISTEMA,
                                  f"Escenario: fase {self.fase + 1} — {config.ESCENARIO[self.fase][0]}")
        t = self.tiempo_escenario
        # A los 45 s la vaca se asusta: un pico corto que NO debe dar alarma
        if 45 <= t < 45 + dt * 1.5 and self.fase == 0:
            self.provocar_pico(duracion=1.5, intensidad=0.28)
            self.registrar_evento(config.EVENTO_SISTEMA, "Escenario: la vaca se asusta y corre un momento")
        # Un ordeño durante la primera fase, para mostrar la balanza
        if 15 <= t < 45:
            self.balanza.fijar_carga(9.0 * config.DENSIDAD_LECHE)
        elif t >= 55:
            self.balanza.fijar_carga(0)
        if 40 <= t < 50 and not self._ordeno_escenario:
            if self.registrar_ordeno(origen="escenario")[0]:
                self._ordeno_escenario = True

    def info_escenario(self):
        """Fase actual, tiempo restante y progreso total, para mostrarlo en pantalla."""
        if self.modo != config.MODO_ESCENARIO:
            return None
        fin_fase = sum(f[2] for f in config.ESCENARIO[:self.fase + 1])
        total = sum(f[2] for f in config.ESCENARIO)
        nombre, _, _, descripcion = config.ESCENARIO[self.fase]
        return {
            "fase": self.fase,
            "total_fases": len(config.ESCENARIO),
            "nombre": nombre,
            "descripcion": descripcion,
            "restante": max(fin_fase - self.tiempo_escenario, 0),
            "progreso": min(self.tiempo_escenario / total, 1.0),
        }

    # =============================================================
    # Comandos (los mismos 5 que recibe el firmware por MQTT)
    # =============================================================
    def ejecutar_comando(self, topico, mensaje):
        """Procesa un comando como lo haría procesar_comando() en la ESP32.

        Devuelve (ok, texto) para que la interfaz informe el resultado.
        """
        if not self.conectado:
            return False, "Sin conexión con la ESP32: el comando no se pudo enviar"

        if topico == config.TOPICO_CFG_UMBRAL:
            valor = float(mensaje)
            if not self.monitor.cambiar_umbral_celo(valor):
                return False, f"Umbral rechazado: debe ser mayor que {self.monitor.umbral_alta}"
            texto = f"Umbral de celo cambiado a {valor:.2f}"
        elif topico == config.TOPICO_CFG_MUESTREO:
            valor = int(mensaje)
            if valor < 500:
                return False, "El intervalo mínimo es 500 ms"
            self.intervalo_publicacion_ms = valor
            texto = f"Intervalo de publicación: {valor / 1000:g} s"
        elif topico == config.TOPICO_CMD_TARA:
            self.balanza.tara()
            texto = "Tara realizada: la balanza quedó en cero"
        elif topico == config.TOPICO_CMD_CALIBRAR:
            peso = float(mensaje)
            if not self.balanza.calibrar(peso):
                return False, "Calibración rechazada: ponga el peso conocido sobre la balanza"
            texto = f"Balanza calibrada con {peso:.2f} kg (factor {self.balanza.factor:.1f})"
        elif topico == config.TOPICO_CMD_BUZZER:
            self.buzzer_silenciado = (mensaje == "silenciar")
            texto = "Buzzer silenciado" if self.buzzer_silenciado else "Buzzer activado"
        else:
            return False, "Comando desconocido"

        self.registrar_evento(config.EVENTO_COMANDO, texto)
        return True, texto

    # =============================================================
    # Acciones que no existen como comando MQTT
    # =============================================================
    def registrar_ordeno(self, origen="pulsador"):
        """Equivale a presionar el pulsador de la balanza."""
        if not self.balanza.es_estable() or self.balanza.litros() <= 0.05:
            return False, "No se registró: el peso no está estable o el balde está vacío"
        litros = self.balanza.litros()
        registro = {
            "ordeno": len(self.registros) + 1,
            "fecha": datetime.now(),
            "litros": round(litros, 2),
            "kg": round(self.balanza.peso_kg(), 2),
            "origen": origen,
        }
        self.registros.append(registro)
        self._publicar(config.TOPICO_REGISTRO, {
            "ordeno": registro["ordeno"],
            "litros": registro["litros"],
            "total": round(sum(r["litros"] for r in self.registros), 2),
        })
        texto = f"Ordeño #{registro['ordeno']} registrado: {registro['litros']:.2f} L"
        if origen == "escenario":
            texto += " (escenario)"
        self.registrar_evento(config.EVENTO_ORDENO, texto)
        return True, texto

    def responder_alerta(self, respuesta):
        """Lo que el ganadero responde a la alerta de posible celo."""
        textos = {
            "confirmar": "Celo confirmado por el ganadero (observado)",
            "falsa": "Alerta marcada como falsa alarma por el ganadero",
        }
        self.registrar_evento(config.EVENTO_ALERTA, textos[respuesta])
        if not self.buzzer_silenciado:
            self.buzzer_silenciado = True

    def cambiar_conexion(self, conectado):
        if conectado == self.conectado:
            return
        self.conectado = conectado
        if conectado:
            self.registrar_evento(config.EVENTO_CONEXION, "Conexión restablecida")
            self._publicar(config.TOPICO_CONEXION, "conectado")
        else:
            # Last Will: el broker avisa que la ESP32 se desconectó
            self.registrar_evento(config.EVENTO_CONEXION, "Conexión perdida (Last Will: desconectado)")

    # =============================================================
    # Registro de eventos y mensajes
    # =============================================================
    def registrar_evento(self, tipo, mensaje):
        self.eventos.append(Evento(tipo, mensaje))
        if len(self.eventos) > config.EVENTOS_GUARDADOS:
            self.eventos.pop(0)

    def _publicar(self, topico, datos):
        """Imita mqtt.publicar(): guarda el mensaje como lo enviaría la ESP32."""
        if not self.conectado:
            return
        carga = datos if isinstance(datos, str) else json.dumps(datos)
        self.mensajes.append({"fecha": datetime.now(), "topico": topico, "carga": carga})
        if len(self.mensajes) > config.MENSAJES_GUARDADOS:
            self.mensajes.pop(0)

    def _cargar_ordenos_de_ejemplo(self):
        """Ordeños de los 5 días anteriores (dos por día), marcados como ejemplo,
        para que el historial no arranque vacío."""
        hoy = datetime.now().replace(minute=0, second=0, microsecond=0)
        for dias in range(5, 0, -1):
            for hora in (5, 16):
                fecha = (hoy - timedelta(days=dias)).replace(hour=hora)
                litros = round(random.uniform(7.0, 11.5), 2)
                self.registros.append({
                    "ordeno": len(self.registros) + 1,
                    "fecha": fecha,
                    "litros": litros,
                    "kg": round(litros * config.DENSIDAD_LECHE, 2),
                    "origen": "ejemplo",
                })

    # =============================================================
    # Estado completo para las vistas
    # =============================================================
    def estado(self):
        """Fotografía del sistema que reciben las pantallas en actualizar()."""
        m, b = self.monitor, self.balanza
        alarma = m.estado == config.ESTADO_CELO
        return {
            "tiempo": self.tiempo,
            "velocidad": self.velocidad,
            "conectado": self.conectado,
            # Simulación
            "modo": self.modo,
            "comportamiento": self.comportamiento,
            "movimiento_simulado": self.movimiento,
            "espontaneos": self.espontaneos,
            "en_pico": self._pico_restante > 0,
            "picos": self.picos,
            "escenario": self.info_escenario(),
            # Actividad
            "estado": m.estado,
            "motivo": m.motivo,
            "actividad": m.actividad,
            "linea_base": m.linea_base,
            "razon": m.razon,
            "umbral_celo": m.umbral_celo,
            "umbral_alta": m.umbral_alta,
            "margen": m.margen,
            "calibrando": m.calibrando,
            "progreso_calibracion": m.progreso_calibracion(),
            "progreso_ventana": m.progreso_ventana(),
            "segundos_para_evaluar": m.segundos_para_evaluar(),
            "muestras_ventana": m.muestras,
            "ventanas": list(m.ventanas),
            "movimientos": list(self.movimientos),
            # Balanza
            "kg": b.peso_kg(),
            "litros": b.litros(),
            "estable": b.es_estable(),
            "carga_objetivo": b.carga_objetivo,
            "factor": b.factor,
            "lecturas_kg": list(self.lecturas_kg),
            "tolerancia_kg": b.tolerancia,
            "ultimas_lecturas": list(b.lecturas),
            # Alarma
            "alarma": alarma,
            "buzzer_sonando": alarma and not self.buzzer_silenciado,
            "buzzer_silenciado": self.buzzer_silenciado,
            # Datos acumulados
            "registros": list(self.registros),
            "eventos": list(self.eventos),
            "mensajes": list(self.mensajes),
            "intervalo_publicacion_ms": self.intervalo_publicacion_ms,
        }
