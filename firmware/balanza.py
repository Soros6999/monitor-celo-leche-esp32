# balanza.py
# Convierte las lecturas del HX711 en kilos y litros de leche,
# y decide si el peso está estable para poder registrar el ordeño.
#
#   kg     = (lectura_cruda - offset) / factor_calibracion
#   litros = kg / densidad_de_la_leche (1.03 kg por litro)

import time


class Balanza:

    def __init__(self, sensor, factor_calibracion, densidad,
                 muestras_estabilidad, tolerancia_kg):
        self.sensor = sensor                  # Objeto HX711
        self.factor = factor_calibracion      # Lecturas crudas por cada kg
        self.densidad = densidad
        self.n_muestras = muestras_estabilidad
        self.tolerancia = tolerancia_kg
        self.offset = 0                       # Lectura cruda con la balanza vacía
        self.lecturas = []                    # Últimas lecturas en kg

    def _promedio_crudo(self, cantidad=5, espera_max_ms=2000):
        """Promedia varias lecturas crudas. Se usa en tara y calibración."""
        suma = 0
        tomadas = 0
        inicio = time.ticks_ms()
        while tomadas < cantidad:
            if time.ticks_diff(time.ticks_ms(), inicio) > espera_max_ms:
                raise OSError("El HX711 no responde")
            if self.sensor.listo():
                suma += self.sensor.leer_crudo()
                tomadas += 1
            time.sleep_ms(5)
        return suma / tomadas

    def tara(self):
        """Pone la balanza en cero con el balde vacío."""
        self.offset = self._promedio_crudo()
        self.lecturas = []

    def calibrar(self, peso_kg):
        """Calcula el factor con un peso conocido puesto sobre la balanza."""
        crudo = self._promedio_crudo() - self.offset
        if peso_kg <= 0 or crudo == 0:
            return False
        self.factor = crudo / peso_kg
        self.lecturas = []
        return True

    def actualizar(self):
        """Toma una lectura si el sensor tiene una lista.

        No espera: si no hay dato, regresa False y el programa sigue.
        """
        if not self.sensor.listo():
            return False
        kg = (self.sensor.leer_crudo() - self.offset) / self.factor
        self.lecturas.append(kg)
        if len(self.lecturas) > self.n_muestras:
            self.lecturas.pop(0)              # Se queda solo con las últimas N
        return True

    def peso_kg(self):
        """Promedio de las últimas lecturas (reduce el ruido)."""
        if not self.lecturas:
            return 0.0
        return sum(self.lecturas) / len(self.lecturas)

    def litros(self):
        """Litros de leche. Un peso negativo se toma como 0."""
        return max(self.peso_kg(), 0.0) / self.densidad

    def es_estable(self):
        """True si las últimas N lecturas varían menos que la tolerancia."""
        if len(self.lecturas) < self.n_muestras:
            return False
        return max(self.lecturas) - min(self.lecturas) < self.tolerancia
