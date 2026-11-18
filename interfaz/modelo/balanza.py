# modelo/balanza.py
# Balanza simulada: imita la celda de carga + HX711 y aplica la MISMA
# lógica de firmware/balanza.py (tara, calibración, litros y estabilidad).
#
#   kg     = (lectura_cruda - offset) / factor
#   litros = kg / 1.03

import random
import config


class BalanzaSimulada:

    PESO_BALDE_KG = 1.2          # Peso del balde vacío (lo quita la tara)
    FACTOR_REAL = 420.0          # Lo que "de verdad" entrega la celda simulada

    def __init__(self, factor_calibracion, densidad, muestras_estabilidad, tolerancia_kg):
        self.factor = factor_calibracion
        self.densidad = densidad
        self.n_muestras = muestras_estabilidad
        self.tolerancia = tolerancia_kg

        self.carga_objetivo = 0.0    # kg de leche que se quieren simular
        self.carga_real = 0.0        # kg que hay en el balde en este momento
        self.offset = 0.0
        self.lecturas = []           # Ventana deslizante de las últimas lecturas (kg)
        self.tara()

    # ---------- Simulación física ----------
    def fijar_carga(self, kg):
        """Cantidad de leche hacia la que se llena (o vacía) el balde."""
        self.carga_objetivo = max(0.0, kg)

    def _leer_crudo(self):
        """Imita la lectura de 24 bits del HX711, con ruido."""
        diferencia = self.carga_objetivo - self.carga_real
        if abs(diferencia) > 0.01:
            # Se está vertiendo: el peso se acerca al objetivo y la leche se mueve
            self.carga_real += diferencia * 0.25
            ruido = random.gauss(0, 0.06)
        else:
            self.carga_real = self.carga_objetivo
            ruido = random.gauss(0, 0.003)
        kg_totales = self.PESO_BALDE_KG + self.carga_real + ruido
        return kg_totales * self.FACTOR_REAL

    # ---------- Misma lógica que el firmware ----------
    def tara(self):
        """Toma la lectura actual como cero (promedio de 5 lecturas)."""
        self.offset = sum(self._leer_crudo() for _ in range(5)) / 5
        self.lecturas = []

    def calibrar(self, peso_kg):
        """Calcula el factor con un peso conocido puesto sobre la balanza.

        Corrige el caso que encontramos en el firmware: si la balanza está
        vacía (lectura neta casi cero), el factor no tendría sentido y se rechaza.
        Se exige una lectura equivalente a más de 100 g.
        """
        crudo = self._leer_crudo() - self.offset
        if peso_kg <= 0 or crudo <= 0.1 * self.factor:
            return False
        self.factor = crudo / peso_kg
        self.lecturas = []
        return True

    def actualizar(self):
        kg = (self._leer_crudo() - self.offset) / self.factor
        self.lecturas.append(kg)
        if len(self.lecturas) > self.n_muestras:
            self.lecturas.pop(0)

    def peso_kg(self):
        if not self.lecturas:
            return 0.0
        return sum(self.lecturas) / len(self.lecturas)

    def litros(self):
        return max(self.peso_kg(), 0.0) / self.densidad

    def es_estable(self):
        if len(self.lecturas) < self.n_muestras:
            return False
        return max(self.lecturas) - min(self.lecturas) < self.tolerancia
