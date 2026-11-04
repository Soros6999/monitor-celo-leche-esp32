# mpu6050.py
# Driver mínimo del acelerómetro MPU6050 por I2C.
# Solo se usa el acelerómetro (no el giroscopio), en el rango de ±2 g.

import struct


class MPU6050:
    # Registros internos del sensor (según la hoja de datos)
    REG_PWR_MGMT_1 = 0x6B       # Control de energía: escribir 0 lo "despierta"
    REG_ACCEL_CONFIG = 0x1C     # Rango del acelerómetro (0 = ±2 g)
    REG_ACCEL_XOUT_H = 0x3B     # Primer registro de los datos de aceleración

    SENSIBILIDAD = 16384.0      # Lecturas crudas por cada 1 g en el rango ±2 g

    def __init__(self, i2c, direccion=0x68):
        self.i2c = i2c
        self.direccion = direccion

        # Comprobar que el sensor responde en el bus I2C
        if direccion not in i2c.scan():
            raise OSError("MPU6050 no encontrado en la dirección 0x{:02X}".format(direccion))

        # El sensor arranca dormido: se despierta y se fija el rango ±2 g
        self.i2c.writeto_mem(direccion, self.REG_PWR_MGMT_1, b"\x00")
        self.i2c.writeto_mem(direccion, self.REG_ACCEL_CONFIG, b"\x00")

    def leer_aceleracion(self):
        """Devuelve (ax, ay, az) en unidades de g."""
        # 6 bytes: X alto, X bajo, Y alto, Y bajo, Z alto, Z bajo
        datos = self.i2c.readfrom_mem(self.direccion, self.REG_ACCEL_XOUT_H, 6)
        # '>hhh' = tres enteros de 16 bits con signo, byte más significativo primero
        ax, ay, az = struct.unpack(">hhh", datos)
        return (ax / self.SENSIBILIDAD,
                ay / self.SENSIBILIDAD,
                az / self.SENSIBILIDAD)
