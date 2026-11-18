# actividad.py
# Calcula el nivel de movimiento de la vaca y decide su estado
# (NORMAL, ACTIVIDAD ALTA o CELO PROBABLE).
#
# Idea:
#   1. Magnitud de la aceleración: |a| = raíz(ax² + ay² + az²).
#      En reposo vale ~1 g (la gravedad), sin importar cómo esté orientado
#      el sensor en el collar.
#   2. Movimiento de una muestra = | |a| - 1 g |.
#   3. Actividad de una ventana = PROMEDIO de esos valores durante 10 s.
#   4. Línea base = actividad "normal" de la vaca (se calibra al inicio).
#   5. Razón = actividad / línea base. Si es >= 2, posible celo.
#   6. Histéresis: para BAJAR de estado, la razón debe quedar por debajo
#      del umbral menos un margen (0.2). Evita que el estado salte de un
#      lado a otro cuando la razón está justo en el límite.

import math
import time
import config


class MonitorActividad:

    def __init__(self, ventana_ms, ventanas_calibracion, alfa,
                 umbral_alta, umbral_celo, linea_base_minima, margen_histeresis=0.0):
        self.ventana_ms = ventana_ms
        self.ventanas_calibracion = ventanas_calibracion
        self.alfa = alfa
        self.umbral_alta = umbral_alta
        self.umbral_celo = umbral_celo
        self.linea_base_minima = linea_base_minima
        self.margen = margen_histeresis

        # Acumuladores de la ventana actual
        self.suma = 0.0
        self.muestras = 0
        self.inicio_ventana = time.ticks_ms()

        # Resultados de la última ventana completa
        self.actividad = 0.0
        self.razon = 0.0
        self.estado = config.ESTADO_NORMAL

        # Calibración de la línea base
        self.calibrando = True
        self.ventanas_calibradas = 0
        self.suma_calibracion = 0.0
        self.linea_base = linea_base_minima

    def agregar_muestra(self, ax, ay, az):
        """Suma el movimiento de una lectura del acelerómetro."""
        magnitud = math.sqrt(ax * ax + ay * ay + az * az)
        self.suma += abs(magnitud - 1.0)
        self.muestras += 1

    def actualizar(self):
        """Cierra la ventana si ya pasaron 'ventana_ms'.

        Devuelve True cuando hay un resultado nuevo (una ventana terminada).
        """
        ahora = time.ticks_ms()
        if time.ticks_diff(ahora, self.inicio_ventana) < self.ventana_ms:
            return False

        # Promedio y no suma: así el resultado no depende de cuántas
        # muestras se tomaron (por si cambia el intervalo de muestreo).
        self.actividad = self.suma / self.muestras if self.muestras else 0.0
        self.suma = 0.0
        self.muestras = 0
        self.inicio_ventana = ahora

        if self.calibrando:
            self._calibrar()
        else:
            self._evaluar()
        return True

    def _calibrar(self):
        """Promedia las primeras ventanas para obtener la actividad normal."""
        self.suma_calibracion += self.actividad
        self.ventanas_calibradas += 1
        if self.ventanas_calibradas >= self.ventanas_calibracion:
            promedio = self.suma_calibracion / self.ventanas_calibradas
            self.linea_base = max(promedio, self.linea_base_minima)
            self.calibrando = False

    def _evaluar(self):
        """Compara la actividad con la línea base y decide el estado."""
        self.razon = self.actividad / self.linea_base
        anterior = self.estado

        # Histéresis: si ya se está en un estado alto, para salir de él
        # la razón debe bajar del umbral MENOS el margen.
        margen_celo = self.margen if anterior == config.ESTADO_CELO else 0.0
        margen_alta = self.margen if anterior in (config.ESTADO_ALTA, config.ESTADO_CELO) else 0.0

        if self.razon >= self.umbral_celo - margen_celo:
            self.estado = config.ESTADO_CELO
        elif self.razon >= self.umbral_alta - margen_alta:
            self.estado = config.ESTADO_ALTA
        else:
            self.estado = config.ESTADO_NORMAL
            # La línea base solo se ajusta con actividad normal; si se ajustara
            # durante un celo, la alerta se iría "diluyendo".
            # Promedio móvil exponencial: nueva = alfa*actual + (1-alfa)*anterior
            nueva = self.alfa * self.actividad + (1 - self.alfa) * self.linea_base
            self.linea_base = max(nueva, self.linea_base_minima)

    def cambiar_umbral_celo(self, valor):
        """Permite cambiar el umbral (lo usará el comando MQTT más adelante)."""
        if valor > self.umbral_alta:
            self.umbral_celo = valor
            return True
        return False
