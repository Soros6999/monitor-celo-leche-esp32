# Monitor de celo y producción de leche en vacas

Proyecto Final de **Programación II** — Universidad Tecnológica de Pereira.
Profesor: Juan Pablo Tabares Cardona.

Firmware en **MicroPython** para una **ESP32** que:

1. **Detecta actividad anormal** de una vaca con un acelerómetro MPU6050 y genera una alerta de *posible celo* (es una alerta, no un diagnóstico).
2. **Mide la leche de cada ordeño** con una celda de carga + HX711 y convierte el peso a litros.
3. **Envía los datos por MQTT** y recibe órdenes de configuración desde una aplicación de escritorio (Parcial 3).

> 🚧 Proyecto en desarrollo — Parcial 2 (firmware).

## Componentes

| Componente | Función |
|---|---|
| ESP32 DevKit | Microcontrolador |
| MPU6050 | Acelerómetro: mide el movimiento de la vaca |
| Celda de carga 50 kg + HX711 | Mide el peso de la leche |
| Pulsador | Guarda el registro de un ordeño |
| LEDs verde, amarillo y rojo | Estado de la vaca |
| Buzzer | Alarma de posible celo |

## Estructura del repositorio

```
firmware/        Código MicroPython que se carga en la ESP32
README.md        Este archivo
```

## Simulación

Enlace a Wokwi: *(pendiente)*
