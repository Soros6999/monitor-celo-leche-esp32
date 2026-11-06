# Simulación interactiva del firmware

`index.html` muestra el banco de pruebas (vaca con collar, protoboard con la ESP32 y balanza de leche) y, a la par, **qué línea de `main.py` se está ejecutando**, las variables y el monitor serial.

## Cómo abrirla

- Doble clic en `docs/simulacion/index.html`. Funciona sin servidor y sin internet (todo va dentro del archivo).
- Para proyectar: pantalla completa del navegador (F11). Está pensada para 1920 × 1080; en pantallas más chicas los paneles se apilan.
- Si se cambia el firmware, se regenera con `node docs/simulacion/build.mjs` (Node 18 o superior). El código que muestra la página se lee de `firmware/*.py` al compilar, y los valores (pines, tiempos, umbrales, tópicos) salen de `config.py`. Con `--dark` se compila en tema oscuro (también hay un botón ◐ en la página).

## Controles

| Control | Qué hace |
|---|---|
| ⏸ Pausa / ▶ Continuar (barra espaciadora) | Congela la simulación con la línea actual resaltada |
| ×1, ×5, ×20 | Velocidad del reloj de la ESP32 (la calibración real dura 30 s) |
| Paso ⏭ (tecla P) | Ejecuta **una vuelta del bucle** línea por línea, entrando a los métodos de cada clase |
| Saltar calibración | Termina la calibración con la actividad actual (se anota en el serial como «simulación») |
| Vista: completa / protoboard / collar / balanza | Zoom de la escena |
| Movimiento de la vaca | 0 a 1 g extra (escala cuadrática para afinar valores pequeños). Atajos: quieta, rumiando 0.03 g, caminando 0.065 g, celo 0.10 g |
| Leche en el balde | 0 a 15 kg; se vierte a 1.2 kg/s y la superficie se agita |
| Pulsador | Clic en el botón azul de la escena o en «Pulsador (GPIO 13)» |
| Cortar WiFi | Apaga el router |
| Comandos de la app | Publican en los tópicos reales: umbral, muestreo, tara, calibrar, silenciar, activar |
| Zoom HX711 | Los 24 pulsos de SCK, los bits de DT, el pulso 25 y el complemento a dos de la última lectura |
| Cursor sobre un cable | Pin, protocolo y la constante de `config.py` |

Flechas ← → avanzan o retroceden en un recorrido.

## Recorridos guiados

1. **Arranque**: creación de objetos, tara, WiFi, conexión MQTT (Last Will, 5 suscripciones, «conectado» retenido) y calibración de 3 ventanas.
2. **Posible celo**: la vaca se mueve, la Tarea 1 lee el MPU6050 cada 100 ms, se cierra la ventana, razón ≥ 2 → LED rojo, buzzer intermitente y publicación de actividad y estado.
3. **Comando desde la app**: llega «silenciar» → `check_msg()` → `_mensaje_recibido` → `procesar_comando` → `buzzer.silenciar(True)`.
4. **Ordeño**: se llena el balde, el peso fluctúa, se rechaza un registro mientras se mueve, se estabiliza, se presiona el botón y se registra y publica.
5. **Se cae la red**: se detecta la caída, el sistema sigue local, reintenta cada 15 s, el broker publica el Last Will «desconectado» a los 90 s y luego se reconecta.

Los recorridos 2 a 5 empiezan desde un estado preparado (arranque rápido y calibración saltada) para no esperar 30 s.

## Cómo se simula

El firmware está reescrito en JavaScript **línea por línea**, siguiendo `main.py` y los métodos de cada clase. Cada paso del simulador apunta a una línea real del archivo (se busca por su texto al cargar la página; si alguna no existiera, aparece un aviso rojo arriba). Los `print` producen los mismos textos y los `mqtt.publicar` el mismo JSON. El reloj virtual solo avanza con los `sleep_ms` y con el tiempo de las operaciones de E/S, así que las tareas se saltan o se ejecutan igual que en la ESP32.

## Simplificaciones respecto al firmware real

- **No corre MicroPython**: es una reproducción en JavaScript de la lógica del firmware.
- **Acelerómetro**: la vaca se modela con senos (0.9, 1.3 y 1.7 Hz) más ruido de 0.004 g, cuantizado a enteros de 16 bits como el MPU6050 (16384 por g). Wokwi entrega valores sin ruido.
- **HX711**: entrega un dato cada 100 ms (10 muestras/s). La lectura cruda es `−20846 + kg × 420` más ruido de ±1.4 cuentas y el oleaje de la leche. `INTERVALO_LECTURA_BALANZA_MS` existe en `config.py` pero `main.py` no lo usa: la balanza se lee cada vez que DT = 0, igual que en el firmware.
- **Pulsador**: rebote mecánico de 3 ms y pulsación mínima de 150 ms de reloj virtual.
- **Red**: asociación WiFi de 1.2 s e IP `10.10.0.2` (la de Wokwi). Al cortar el WiFi, la siguiente operación de red falla con `[Errno 104] ECONNRESET`; el texto exacto del error en una ESP32 real puede variar. El broker usa QoS 0 y cierra la sesión a 1.5 × keepalive = 90 s, momento en que publica el Last Will. Los paquetes tardan 1.1 s reales por tramo en la animación, sin importar la velocidad.
- **Formato de números**: se imita el float de 32 bits de MicroPython en los `print` y en el JSON (por ejemplo `2.0`, `419.8765`).
- **Orden de llaves del JSON**: el del código (MicroPython no garantiza ese orden).

## Observaciones del firmware que muestra la simulación

- **Reconexión bloqueante**: `_conectar_wifi()` espera al router con un `while` + `sleep_ms(200)` de hasta `WIFI_TIMEOUT_MS` = 10 s. Sin WiFi, `revisar()` reintenta cada 15 s, así que el bucle queda detenido unos 10 de cada 15 s: no se leen sensores, el botón no responde y el buzzer queda congelado en su último estado. La página lo marca con un aviso «Bucle detenido». El primer reintento ocurre en cuanto se detecta la caída, porque `ultimo_intento` se fijó en la conexión anterior.
- **Tercera ventana de calibración**: cuando `_calibrar()` termina, `calibrando` ya es `False`, así que `main.py` imprime y publica esa ventana como «[Vaca] … Razón: 0.00 | NORMAL» (la razón todavía no se calculó). No aparece «Calibrando... ventana 3 de 3».
- **Calibrar con la balanza vacía**: `calibrar(10)` sin peso encima solo rechaza `crudo == 0`; con el ruido normal da un factor absurdo (por ejemplo `-0.18`) y desde ahí los kilos salen mal. Hay que poner el peso conocido antes de enviar el comando, o volver a reiniciar.
- **Línea base mínima**: si la vaca está casi quieta durante la calibración, la línea base queda en `LINEA_BASE_MINIMA` = 0.02 g; con eso, «caminando» (0.065 g) ya da actividad alta.
