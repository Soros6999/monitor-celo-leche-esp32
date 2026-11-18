# modelo/actividad.py
# Lógica de detección de posible celo.
#
# Es la MISMA lógica de firmware/actividad.py, adaptada a la simulación:
# en la ESP32 el tiempo lo da time.ticks_ms(); aquí lo pone el simulador
# con avanzar(dt). Así la interfaz muestra exactamente lo que haría la ESP32.
#
#   1. Magnitud: |a| = raíz(ax² + ay² + az²)  -> en reposo vale 1 g.
#   2. Movimiento de una muestra = | |a| - 1 g |.
#   3. Actividad = PROMEDIO del movimiento en una ventana de 10 s.
#   4. Línea base = actividad normal (3 ventanas de calibración y luego
#      promedio móvil exponencial, solo en estado NORMAL).
#   5. Razón = actividad / línea base  -> decide el estado, con histéresis.

import math
import config

# Orden de los estados: sirve para saber si el estado "sube" o "baja"
NIVEL = {config.ESTADO_NORMAL: 0, config.ESTADO_ALTA: 1, config.ESTADO_CELO: 2}


class MonitorActividad:

    def __init__(self, ventana_s, ventanas_calibracion, alfa,
                 umbral_alta, umbral_celo, linea_base_minima, margen_histeresis):
        self.ventana_s = ventana_s
        self.ventanas_calibracion = ventanas_calibracion
        self.alfa = alfa
        self.umbral_alta = umbral_alta
        self.umbral_celo = umbral_celo
        self.linea_base_minima = linea_base_minima
        self.margen = margen_histeresis

        # Ventana actual
        self.suma = 0.0
        self.muestras = 0
        self.tiempo_ventana = 0.0
        self.ultimo_movimiento = 0.0

        # Resultado de la última ventana cerrada
        self.actividad = 0.0
        self.razon = 0.0
        self.estado = config.ESTADO_CALIBRANDO
        self.motivo = "Calibrando la línea base"   # Explicación de la última decisión

        # Calibración de la línea base
        self.calibrando = True
        self.ventanas_calibradas = 0
        self.suma_calibracion = 0.0
        self.linea_base = linea_base_minima

        # Historial de ventanas cerradas (para la gráfica): lista de diccionarios
        self.ventanas = []

    # ---------- Entrada de datos ----------
    def agregar_muestra(self, ax, ay, az):
        """Suma el movimiento de una lectura del acelerómetro."""
        magnitud = math.sqrt(ax * ax + ay * ay + az * az)
        self.ultimo_movimiento = abs(magnitud - 1.0)
        self.suma += self.ultimo_movimiento
        self.muestras += 1

    def avanzar(self, dt):
        """Avanza el reloj de la ventana. Devuelve True si cerró una ventana."""
        self.tiempo_ventana += dt
        if self.tiempo_ventana < self.ventana_s - 1e-9:
            return False
        self._cerrar_ventana()
        return True

    # ---------- Lógica interna ----------
    def _cerrar_ventana(self):
        self.actividad = self.suma / self.muestras if self.muestras else 0.0
        self.suma = 0.0
        self.muestras = 0
        self.tiempo_ventana = 0.0

        if self.calibrando:
            self._calibrar()
        else:
            self._evaluar()

        self.ventanas.append({
            "actividad": self.actividad,
            "linea_base": self.linea_base,
            "razon": self.razon,
            "estado": self.estado,
        })
        if len(self.ventanas) > config.VENTANAS_EN_GRAFICA:
            self.ventanas.pop(0)

    def _calibrar(self):
        self.suma_calibracion += self.actividad
        self.ventanas_calibradas += 1
        if self.ventanas_calibradas >= self.ventanas_calibracion:
            promedio = self.suma_calibracion / self.ventanas_calibradas
            self.linea_base = max(promedio, self.linea_base_minima)
            self.calibrando = False
            self.estado = config.ESTADO_NORMAL
            self.razon = self.actividad / self.linea_base
            self.motivo = f"Línea base calibrada en {self.linea_base:.4f} g"
        else:
            self.motivo = f"Calibrando: ventana {self.ventanas_calibradas} de {self.ventanas_calibracion}"

    def _clasificar(self, razon, margen_alta, margen_celo):
        if razon >= self.umbral_celo - margen_celo:
            return config.ESTADO_CELO
        if razon >= self.umbral_alta - margen_alta:
            return config.ESTADO_ALTA
        return config.ESTADO_NORMAL

    def _evaluar(self):
        self.razon = self.actividad / self.linea_base
        anterior = self.estado

        # Histéresis: si ya se está en un estado alto, para salir de él la
        # razón debe bajar del umbral MENOS el margen.
        margen_celo = self.margen if anterior == config.ESTADO_CELO else 0.0
        margen_alta = self.margen if NIVEL.get(anterior, 0) >= 1 else 0.0
        self.estado = self._clasificar(self.razon, margen_alta, margen_celo)

        if self.estado == anterior and self.estado != config.ESTADO_NORMAL and \
                self.estado != self._clasificar(self.razon, 0.0, 0.0):
            self.motivo = (f"Razón {self.razon:.2f}: se mantiene por histéresis "
                           f"(baja solo con menos de {self._umbral_salida():.2f})")
        else:
            self.motivo = f"Razón {self.razon:.2f} → {config.NOMBRE_ESTADO[self.estado]}"

        if self.estado == config.ESTADO_NORMAL:
            # Solo con actividad normal se ajusta la línea base
            nueva = self.alfa * self.actividad + (1 - self.alfa) * self.linea_base
            self.linea_base = max(nueva, self.linea_base_minima)

    def _umbral_salida(self):
        if self.estado == config.ESTADO_CELO:
            return self.umbral_celo - self.margen
        return self.umbral_alta - self.margen

    # ---------- Consultas y comandos ----------
    def progreso_ventana(self):
        """Fracción (0 a 1) de la ventana actual que ya transcurrió."""
        return min(self.tiempo_ventana / self.ventana_s, 1.0)

    def segundos_para_evaluar(self):
        return max(self.ventana_s - self.tiempo_ventana, 0.0)

    def progreso_calibracion(self):
        return self.ventanas_calibradas / self.ventanas_calibracion

    def cambiar_umbral_celo(self, valor):
        """Igual que en el firmware: debe ser mayor que el umbral de actividad alta."""
        if valor > self.umbral_alta:
            self.umbral_celo = valor
            return True
        return False
