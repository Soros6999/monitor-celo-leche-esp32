// sim.js — Simulador del firmware y de la planta física.
// Se incrusta en index.html. FUENTES (texto exacto de firmware/*.py) y CFG
// (valores de config.py) los inyecta build.mjs al compilar.
//
// El firmware se reescribe como generadores de JavaScript que siguen
// main.py LÍNEA POR LÍNEA: cada `yield* L(archivo, "texto de la línea")`
// marca la línea real que se está ejecutando (se busca su número en el
// archivo original al cargar la página; si una línea no existe, la página
// lo avisa en rojo). Los `sleep_ms` hacen avanzar el reloj virtual.

/* global FUENTES, CFG, ESCENA, translateAlong, iso */

// ======================================================================
// 1. Localizador de líneas del código real
// ======================================================================
const LINEAS = {};
for (const [f, txt] of Object.entries(FUENTES)) LINEAS[f] = txt.replace(/\r/g, "").split("\n");
const cacheL = new Map();
const erroresLinea = [];
function lineaDe(f, texto, en) {
  const clave = f + "|" + texto + "|" + (en || "");
  if (cacheL.has(clave)) return cacheL.get(clave);
  const ls = LINEAS[f];
  let desde = 0;
  if (en) {
    desde = ls.findIndex((l) => l.includes(en));
    if (desde < 0) { erroresLinea.push(`${f}: no existe «${en}»`); desde = 0; }
  }
  let i = ls.findIndex((l, j) => j >= desde && l.trim().startsWith(texto));
  if (i < 0) i = ls.findIndex((l, j) => j >= desde && l.includes(texto));
  if (i < 0) { erroresLinea.push(`${f}: no existe «${texto}»`); i = 0; }
  cacheL.set(clave, i + 1);
  return i + 1;
}

// ======================================================================
// 2. Reloj virtual y mundo físico
// ======================================================================
const G = 1.0;
const HW = {
  t: 0,                 // ms virtuales desde el arranque
  // vaca
  amp: 0.03,            // g de movimiento extra (control)
  ax: 0, ay: 0, az: 1,  // última muestra física (para el balanceo del collar)
  // balanza
  kgObjetivo: 0, kg: 0, vertiendo: false, oleaje: 0,
  hxListo: false, hxCrudo: 0, hxProx: 100, hxUltimo: null,
  // botón (pull-up: 1 suelto, 0 presionado)
  botonAbajo: false, botonCambio: -1e9, botonSoltarEn: null,
  // WiFi y broker
  wifi: true, asociado: false, asociadoEn: null,
  // salidas que maneja el firmware
  led: { verde: 0, amarillo: 0, rojo: 0 }, pwm: 0,
  i2cFlash: 0, hxFlash: 0,
};
const OFFSET_HW = -20846;      // lectura cruda con el balde vacío (incluye el balde)
const FACTOR_HW = 420;          // cuentas por kg reales de la celda
let semilla = 7;
const azar = () => ((semilla = (semilla * 16807) % 2147483647) / 2147483647);
const gauss = () => { let s = 0; for (let i = 0; i < 6; i++) s += azar(); return (s - 3) / Math.sqrt(0.5); };
const ticks = () => Math.floor(HW.t);

function avanzar(ms) {
  const fin = HW.t + ms;
  while (HW.t < fin - 1e-9) {
    const dt = Math.min(10, fin - HW.t);
    HW.t += dt;
    // vertido de leche: 1.2 kg/s hacia el objetivo; vaciar es más rápido
    const dif = HW.kgObjetivo - HW.kg;
    if (dif > 0.0005) { const paso = Math.min(dif, 1.2 * dt / 1000); HW.kg += paso; HW.vertiendo = true; HW.oleaje = Math.min(0.35, HW.oleaje + 0.9 * dt / 1000); }
    else if (dif < -0.0005) { HW.kg += Math.max(dif, -4 * dt / 1000); HW.vertiendo = false; HW.oleaje = Math.min(0.35, HW.oleaje + 0.6 * dt / 1000); }
    else { HW.kg = HW.kgObjetivo; HW.vertiendo = false; }
    HW.oleaje *= Math.exp(-dt / 900);
    if (HW.oleaje < 1e-5) HW.oleaje = 0;
    // conversión del HX711 cada 100 ms (10 muestras/s): DT baja a 0
    if (HW.t >= HW.hxProx) {
      HW.hxProx += 100;
      const ola = HW.oleaje * Math.sin(HW.t / 1000 * 2 * Math.PI * 2.3) + HW.oleaje * 0.4 * Math.sin(HW.t / 1000 * 2 * Math.PI * 5.1);
      HW.hxCrudo = Math.round(OFFSET_HW + (HW.kg + ola) * FACTOR_HW + gauss() * 1.4);
      HW.hxListo = true;
    }
    // asociación WiFi (tarda ~1.2 s cuando se pide conectar)
    if (!HW.wifi) { HW.asociado = false; HW.asociadoEn = null; }
    else if (HW.asociadoEn !== null && HW.t >= HW.asociadoEn) { HW.asociado = true; HW.asociadoEn = null; }
    if (HW.botonSoltarEn !== null && HW.t >= HW.botonSoltarEn) { HW.botonSoltarEn = null; soltarBoton(true); }
    RED.tic();
  }
}
function muestraMPU() {
  const s = HW.t / 1000, A = HW.amp;
  const ax = A * 0.55 * Math.sin(2 * Math.PI * 0.9 * s) + gauss() * 0.004;
  const ay = A * 0.35 * Math.sin(2 * Math.PI * 1.7 * s + 1) + gauss() * 0.004;
  const az = G + A * 0.8 * Math.sin(2 * Math.PI * 1.3 * s + 0.5) + gauss() * 0.004;
  // el MPU6050 entrega enteros de 16 bits (±2 g → 16384 por g)
  const q = (v) => Math.max(-32768, Math.min(32767, Math.round(v * 16384)));
  return [q(ax), q(ay), q(az)];
}
function pinBoton() {
  const desde = HW.t - HW.botonCambio;
  const base = HW.botonAbajo ? 0 : 1;
  if (desde < 3) return Math.floor(desde * 2.7) % 2 ? 1 - base : base; // rebote mecánico
  return base;
}
function presionarBoton() {
  if (HW.botonAbajo) return;
  HW.botonAbajo = true; HW.botonCambio = HW.t; HW.botonSoltarEn = null; HW.botonDesde = performance.now();
  UI.boton(true);
}
function soltarBoton(forzado) {
  if (!HW.botonAbajo) return;
  // se mantiene presionado al menos 150 ms virtuales (más que el antirrebote)
  if (!forzado && HW.t - HW.botonCambio < 150) { HW.botonSoltarEn = HW.botonCambio + 150; return; }
  HW.botonAbajo = false; HW.botonCambio = HW.t;
  UI.boton(false);
}

// ======================================================================
// 3. Red: broker MQTT y aplicación
// ======================================================================
const RED = {
  sesion: false, ultimaActividad: 0, retenido: { [CFG.TOPICO_CONEXION]: null },
  buzon: [],            // mensajes que el broker ya entregó al socket de la ESP32
  socketMuerto: false,
  app: {},
  tic() {
    // el broker cierra la sesión si no oye a la ESP32 en 1.5 × keepalive
    if (this.sesion && HW.t - this.ultimaActividad > 1.5 * CFG.MQTT_KEEPALIVE_S * 1000) {
      this.sesion = false;
      this.retenido[CFG.TOPICO_CONEXION] = "desconectado";
      UI.paquete("broker", "app", CFG.TOPICO_CONEXION, "desconectado", { will: true });
      UI.log("broker", "Keepalive vencido (" + (1.5 * CFG.MQTT_KEEPALIVE_S) + " s sin noticias): el broker publica el Last Will");
    }
  },
  desdeEsp(topico, texto, extra = {}) {
    if (!HW.wifi || this.socketMuerto) { UI.paquete("esp", "broker", topico, texto, { perdido: true }); return false; }
    this.ultimaActividad = HW.t;
    UI.paquete("esp", "broker", topico, texto, { ...extra, siguiente: this.sesion ? () => { this.app[topico] = texto; UI.app(topico, texto); } : null });
    return true;
  },
  desdeApp(topico, texto) {
    UI.paquete("app", "broker", topico, texto, {
      llega: () => {
        if (this.sesion && HW.wifi && !this.socketMuerto) UI.paquete("broker", "esp", topico, texto, { llega: () => this.buzon.push({ topico, texto }) });
        else UI.log("broker", "La ESP32 no está conectada: el mensaje (QoS 0) se descarta");
      },
    });
  },
};

// ======================================================================
// 4. Estado del firmware (nombres iguales a los del código)
// ======================================================================
const FW = {};
function reiniciarFW() {
  Object.assign(FW, {
    fase: "arranque", ahora: 0, ultima_lectura_mpu: 0, ultima_publicacion_peso: 0,
    intervalo_publicacion: CFG.INTERVALO_PUBLICACION_MS, registros: [],
    ax: 0, ay: 0, az: 0, estable: false, valor: null,
    monitor: { suma: 0, muestras: 0, inicio_ventana: 0, actividad: 0, razon: 0, estado: CFG.ESTADO_NORMAL, calibrando: true, ventanas_calibradas: 0, suma_calibracion: 0, linea_base: CFG.LINEA_BASE_MINIMA, umbral_celo: CFG.UMBRAL_CELO, umbral_alta: CFG.UMBRAL_ACTIVIDAD_ALTA },
    balanza: { offset: 0, factor: CFG.FACTOR_CALIBRACION, lecturas: [] },
    buzzer: { activo: false, silenciado: false, sonando: false, ultimo_cambio: 0 },
    boton: { estado_estable: 1, ultima_lectura: 1, tiempo_cambio: 0 },
    mqtt: { conectado: false, ultimo_intento: 0, ultimo_ping: 0 },
  });
}
reiniciarFW();
const pesoKg = () => FW.balanza.lecturas.length ? FW.balanza.lecturas.reduce((a, b) => a + b, 0) / FW.balanza.lecturas.length : 0;
const litros = () => Math.max(pesoKg(), 0) / CFG.DENSIDAD_LECHE;
const esEstable = () => FW.balanza.lecturas.length < CFG.MUESTRAS_ESTABILIDAD ? false : Math.max(...FW.balanza.lecturas) - Math.min(...FW.balanza.lecturas) < CFG.TOLERANCIA_ESTABLE_KG;
const diff = (a, b) => a - b;

// Formato de Python/MicroPython
const f32 = (x) => Math.fround(x);
function pyFloat(x) {
  if (!isFinite(x)) return String(x);
  if (Number.isInteger(x)) return x.toFixed(1);
  let s = String(Number(f32(x).toPrecision(7)));
  if (/e/.test(s)) return s;
  if (!s.includes(".")) s += ".0";
  return s;
}
const pyVal = (v) => typeof v === "number" ? (Number.isInteger(v) && !v.__float ? String(v) : pyFloat(v)) : typeof v === "boolean" ? (v ? "True" : "False") : String(v);
const fmt = (x, d) => (Math.round(x * 10 ** d) / 10 ** d).toFixed(d);
const redondear = (x, d) => Math.round(x * 10 ** d) / 10 ** d;
function jsonDumps(obj) {
  return "{" + Object.entries(obj).map(([k, v]) => `"${k}": ${typeof v === "string" ? JSON.stringify(v) : typeof v === "boolean" ? String(v) : (v.f ? pyFloat(v.v) : String(v))}`).join(", ") + "}";
}
const F = (v) => ({ f: true, v });  // marca un número como float de Python

// ======================================================================
// 5. Firmware como generadores
// ======================================================================
const M = "main.py", A = "actividad.py", B = "balanza.py", HX = "hx711.py", IND = "indicadores.py", BOT = "boton.py", MPU = "mpu6050.py", COM = "comunicacion.py";
function* L(f, texto, op = {}) {
  yield { tipo: "linea", f, l: lineaDe(f, texto, op.en), n: op.n || 1, rapido: op.rapido, nota: op.nota };
}
function* llamar(f, def, cuerpo) {
  yield { tipo: "entrar", f, l: lineaDe(f, def), def };
  const r = yield* cuerpo();
  yield { tipo: "salir", f };
  return r;
}
function* dormir(ms) { yield { tipo: "dormir", ms }; }
const tarea = (n, estado, motivo) => ({ tipo: "tarea", n, estado, motivo });
function serial(texto) { UI.serial(texto); return { tipo: "print", texto }; }

// ---- hx711.py ----
function* hxListo() {
  return yield* llamar(HX, "def listo", function* () {
    yield* L(HX, "return self.dt.value() == 0");
    return HW.hxListo;
  });
}
function* hxLeerCrudo() {
  return yield* llamar(HX, "def leer_crudo", function* () {
    yield* L(HX, "estado = machine.disable_irq()");
    yield* L(HX, "valor = 0", { en: "def leer_crudo" });
    const crudo = HW.hxCrudo;
    const bits = (crudo & 0xffffff) >>> 0;
    HW.hxListo = false; HW.hxFlash = performance.now();
    yield* L(HX, "for _ in range(24):", { nota: "24 pulsos de SCK: un bit de DT por pulso" });
    yield* L(HX, "self.sck.on()", { en: "for _ in range(24)", rapido: true });
    yield* L(HX, "self.sck.off()", { en: "for _ in range(24)", rapido: true });
    yield* L(HX, "valor = (valor << 1) | self.dt.value()", { rapido: true });
    yield* L(HX, "self.sck.on()                                # Pulso 25", { nota: "pulso 25: canal A, ganancia 128" });
    yield* L(HX, "machine.enable_irq(estado)");
    avanzar(0.06);
    yield* L(HX, "if valor & 0x800000:");
    let valor = bits;
    if (valor & 0x800000) { yield* L(HX, "valor -= 0x1000000"); valor -= 0x1000000; }
    yield* L(HX, "return valor", { en: "def leer_crudo" });
    HW.hxUltimo = { bits, valor, t: HW.t };
    UI.hxZoom(HW.hxUltimo);
    return valor;
  });
}
// ---- balanza.py ----
function* promedioCrudo() {
  return yield* llamar(B, "def _promedio_crudo", function* () {
    yield* L(B, "suma = 0", { en: "def _promedio_crudo" });
    yield* L(B, "tomadas = 0");
    yield* L(B, "inicio = time.ticks_ms()", { en: "def _promedio_crudo" });
    let suma = 0, tomadas = 0;
    while (true) {
      yield* L(B, "while tomadas < cantidad:", { rapido: true });
      if (!(tomadas < 5)) break;
      yield* L(B, "if time.ticks_diff(time.ticks_ms(), inicio) > espera_max_ms:", { rapido: true });
      yield* L(B, "if self.sensor.listo():", { rapido: true });
      if (HW.hxListo) {
        yield* L(B, "suma += self.sensor.leer_crudo()", { rapido: true });
        HW.hxListo = false; HW.hxFlash = performance.now();
        suma += HW.hxCrudo; tomadas++;
        yield* L(B, "tomadas += 1", { rapido: true });
      }
      yield* L(B, "time.sleep_ms(5)", { en: "def _promedio_crudo", rapido: true });
      yield* dormir(5);
    }
    yield* L(B, "return suma / tomadas");
    return suma / tomadas;
  });
}
function* balanzaTara() {
  return yield* llamar(B, "def tara", function* () {
    yield* L(B, "self.offset = self._promedio_crudo()");
    FW.balanza.offset = yield* promedioCrudo();
    yield* L(B, "self.lecturas = []", { en: "def tara" });
    FW.balanza.lecturas = [];
  });
}
function* balanzaCalibrar(peso) {
  return yield* llamar(B, "def calibrar", function* () {
    yield* L(B, "crudo = self._promedio_crudo() - self.offset");
    const crudo = (yield* promedioCrudo()) - FW.balanza.offset;
    yield* L(B, "if peso_kg <= 0 or crudo == 0:");
    if (peso <= 0 || crudo === 0) { yield* L(B, "return False", { en: "def calibrar" }); return false; }
    yield* L(B, "self.factor = crudo / peso_kg");
    FW.balanza.factor = crudo / peso;
    yield* L(B, "self.lecturas = []", { en: "def calibrar" });
    FW.balanza.lecturas = [];
    yield* L(B, "return True", { en: "def calibrar" });
    return true;
  });
}
function* balanzaActualizar() {
  return yield* llamar(B, "def actualizar", function* () {
    yield* L(B, "if not self.sensor.listo():");
    const listo = yield* hxListo();
    if (!listo) { yield* L(B, "return False", { en: "def actualizar" }); return false; }
    yield* L(B, "kg = (self.sensor.leer_crudo() - self.offset) / self.factor");
    const crudo = yield* hxLeerCrudo();
    const kg = (crudo - FW.balanza.offset) / FW.balanza.factor;
    yield* L(B, "self.lecturas.append(kg)");
    FW.balanza.lecturas.push(kg);
    yield* L(B, "if len(self.lecturas) > self.n_muestras:");
    if (FW.balanza.lecturas.length > CFG.MUESTRAS_ESTABILIDAD) { yield* L(B, "self.lecturas.pop(0)"); FW.balanza.lecturas.shift(); }
    yield* L(B, "return True", { en: "def actualizar" });
    return true;
  });
}
function* balanzaEsEstable() {
  return yield* llamar(B, "def es_estable", function* () {
    yield* L(B, "if len(self.lecturas) < self.n_muestras:");
    if (FW.balanza.lecturas.length < CFG.MUESTRAS_ESTABILIDAD) { yield* L(B, "return False", { en: "def es_estable" }); return false; }
    yield* L(B, "return max(self.lecturas) - min(self.lecturas) < self.tolerancia");
    return esEstable();
  });
}
// ---- actividad.py ----
function* agregarMuestra(ax, ay, az) {
  return yield* llamar(A, "def agregar_muestra", function* () {
    yield* L(A, "magnitud = math.sqrt(ax * ax + ay * ay + az * az)");
    const magnitud = Math.sqrt(ax * ax + ay * ay + az * az);
    yield* L(A, "self.suma += abs(magnitud - 1.0)");
    FW.monitor.suma += Math.abs(magnitud - 1.0);
    yield* L(A, "self.muestras += 1");
    FW.monitor.muestras += 1;
    FW.magnitud = magnitud;
  });
}
function* monitorActualizar() {
  return yield* llamar(A, "def actualizar", function* () {
    const m = FW.monitor;
    yield* L(A, "ahora = time.ticks_ms()", { en: "def actualizar" });
    const ahora = ticks();
    yield* L(A, "if time.ticks_diff(ahora, self.inicio_ventana) < self.ventana_ms:");
    if (diff(ahora, m.inicio_ventana) < CFG.VENTANA_ACTIVIDAD_MS) { yield* L(A, "return False", { en: "def actualizar" }); return false; }
    yield* L(A, "self.actividad = self.suma / self.muestras if self.muestras else 0.0");
    m.actividad = m.muestras ? m.suma / m.muestras : 0.0;
    yield* L(A, "self.suma = 0.0", { en: "def actualizar" }); m.suma = 0;
    yield* L(A, "self.muestras = 0", { en: "def actualizar" }); m.muestras = 0;
    yield* L(A, "self.inicio_ventana = ahora"); m.inicio_ventana = ahora;
    yield* L(A, "if self.calibrando:", { en: "def actualizar" });
    if (m.calibrando) {
      yield* L(A, "self._calibrar()");
      yield* llamar(A, "def _calibrar", function* () {
        yield* L(A, "self.suma_calibracion += self.actividad"); m.suma_calibracion += m.actividad;
        yield* L(A, "self.ventanas_calibradas += 1"); m.ventanas_calibradas += 1;
        yield* L(A, "if self.ventanas_calibradas >= self.ventanas_calibracion:");
        if (m.ventanas_calibradas >= CFG.VENTANAS_CALIBRACION) {
          yield* L(A, "promedio = self.suma_calibracion / self.ventanas_calibradas");
          const promedio = m.suma_calibracion / m.ventanas_calibradas;
          yield* L(A, "self.linea_base = max(promedio, self.linea_base_minima)");
          m.linea_base = Math.max(promedio, CFG.LINEA_BASE_MINIMA);
          yield* L(A, "self.calibrando = False"); m.calibrando = false;
        }
      });
    } else {
      yield* L(A, "self._evaluar()");
      yield* llamar(A, "def _evaluar", function* () {
        yield* L(A, "self.razon = self.actividad / self.linea_base"); m.razon = m.actividad / m.linea_base;
        yield* L(A, "if self.razon >= self.umbral_celo:");
        if (m.razon >= m.umbral_celo) { yield* L(A, "self.estado = config.ESTADO_CELO"); m.estado = CFG.ESTADO_CELO; return; }
        yield* L(A, "elif self.razon >= self.umbral_alta:");
        if (m.razon >= m.umbral_alta) { yield* L(A, "self.estado = config.ESTADO_ALTA"); m.estado = CFG.ESTADO_ALTA; return; }
        yield* L(A, "self.estado = config.ESTADO_NORMAL", { en: "def _evaluar" }); m.estado = CFG.ESTADO_NORMAL;
        yield* L(A, "nueva = self.alfa * self.actividad + (1 - self.alfa) * self.linea_base");
        const nueva = CFG.ALFA_LINEA_BASE * m.actividad + (1 - CFG.ALFA_LINEA_BASE) * m.linea_base;
        yield* L(A, "self.linea_base = max(nueva, self.linea_base_minima)"); m.linea_base = Math.max(nueva, CFG.LINEA_BASE_MINIMA);
      });
    }
    yield* L(A, "return True", { en: "def actualizar" });
    return true;
  });
}
// ---- indicadores.py ----
function* semaforoMostrar(estado) {
  return yield* llamar(IND, "def mostrar", function* () {
    yield* L(IND, "self.verde.value(1 if estado == config.ESTADO_NORMAL else 0)"); HW.led.verde = estado === CFG.ESTADO_NORMAL ? 1 : 0;
    yield* L(IND, "self.amarillo.value(1 if estado == config.ESTADO_ALTA else 0)"); HW.led.amarillo = estado === CFG.ESTADO_ALTA ? 1 : 0;
    yield* L(IND, "self.rojo.value(1 if estado == config.ESTADO_CELO else 0)"); HW.led.rojo = estado === CFG.ESTADO_CELO ? 1 : 0;
  });
}
function* tono(encender) {
  return yield* llamar(IND, "def _tono", function* () {
    yield* L(IND, "self.sonando = encender"); FW.buzzer.sonando = encender;
    yield* L(IND, "self.pwm.duty_u16(32768 if encender else 0)"); HW.pwm = encender ? 32768 : 0;
  });
}
function* buzzerActivar() { return yield* llamar(IND, "def activar", function* () { yield* L(IND, "self.activo = True", { en: "def activar" }); FW.buzzer.activo = true; }); }
function* buzzerDesactivar() {
  return yield* llamar(IND, "def desactivar", function* () {
    yield* L(IND, "self.activo = False", { en: "def desactivar" }); FW.buzzer.activo = false;
    yield* L(IND, "self.silenciado = False", { en: "def desactivar" }); FW.buzzer.silenciado = false;
    yield* L(IND, "self._tono(False)", { en: "def desactivar" }); yield* tono(false);
  });
}
function* buzzerSilenciar(valor) {
  return yield* llamar(IND, "def silenciar", function* () {
    yield* L(IND, "self.silenciado = valor"); FW.buzzer.silenciado = valor;
    yield* L(IND, "if valor:", { en: "def silenciar" });
    if (valor) { yield* L(IND, "self._tono(False)", { en: "def silenciar" }); yield* tono(false); }
  });
}
function* buzzerActualizar() {
  return yield* llamar(IND, "def actualizar", function* () {
    const b = FW.buzzer;
    yield* L(IND, "if not self.activo or self.silenciado:");
    if (!b.activo || b.silenciado) { yield* L(IND, "return", { en: "if not self.activo or self.silenciado:" }); return b.activo ? "silenciado" : "inactivo"; }
    yield* L(IND, "ahora = time.ticks_ms()", { en: "def actualizar" });
    const ahora = ticks();
    yield* L(IND, "if time.ticks_diff(ahora, self.ultimo_cambio) >= self.intervalo:");
    if (diff(ahora, b.ultimo_cambio) >= CFG.BUZZER_INTERVALO_MS) {
      yield* L(IND, "self.ultimo_cambio = ahora"); b.ultimo_cambio = ahora;
      yield* L(IND, "self._tono(not self.sonando)"); yield* tono(!b.sonando);
      return "cambio";
    }
    return CFG.BUZZER_INTERVALO_MS - diff(ahora, b.ultimo_cambio);
  });
}
// ---- boton.py ----
function* botonFuePresionado() {
  return yield* llamar(BOT, "def fue_presionado", function* () {
    const b = FW.boton;
    yield* L(BOT, "lectura = self.pin.value()", { en: "def fue_presionado" });
    const lectura = pinBoton();
    yield* L(BOT, "ahora = time.ticks_ms()", { en: "def fue_presionado" });
    const ahora = ticks();
    yield* L(BOT, "if lectura != self.ultima_lectura:");
    if (lectura !== b.ultima_lectura) {
      yield* L(BOT, "self.ultima_lectura = lectura"); b.ultima_lectura = lectura;
      yield* L(BOT, "self.tiempo_cambio = ahora"); b.tiempo_cambio = ahora;
      yield* L(BOT, "return False", { en: "if lectura != self.ultima_lectura:" });
      return { r: false, motivo: "cambió la lectura: empieza el antirrebote" };
    }
    yield* L(BOT, "if (lectura != self.estado_estable and");
    if (lectura !== b.estado_estable && diff(ahora, b.tiempo_cambio) >= CFG.ANTIRREBOTE_MS) {
      yield* L(BOT, "self.estado_estable = lectura"); b.estado_estable = lectura;
      yield* L(BOT, "return lectura == 0");
      return { r: lectura === 0, motivo: lectura === 0 ? null : "se soltó el botón" };
    }
    yield* L(BOT, "return False", { en: "# Si la lectura se mantuvo estable" });
    if (lectura !== b.estado_estable) return { r: false, motivo: `antirrebote: faltan ${CFG.ANTIRREBOTE_MS - diff(ahora, b.tiempo_cambio)} ms` };
    return { r: false, motivo: "sin pulsación nueva" };
  });
}
// ---- mpu6050.py ----
function* leerAceleracion() {
  return yield* llamar(MPU, "def leer_aceleracion", function* () {
    yield* L(MPU, "datos = self.i2c.readfrom_mem(self.direccion, self.REG_ACCEL_XOUT_H, 6)");
    const [rx, ry, rz] = muestraMPU();
    HW.i2cFlash = performance.now();
    avanzar(0.25);
    yield* L(MPU, "ax, ay, az = struct.unpack(\">hhh\", datos)");
    yield* L(MPU, "return (ax / self.SENSIBILIDAD,", { n: 3 });
    const S = 16384.0;
    HW.ax = rx / S; HW.ay = ry / S; HW.az = rz / S;
    return [rx / S, ry / S, rz / S];
  });
}
// ---- comunicacion.py ----
const ERR_RED = "[Errno 104] ECONNRESET";
function* conectarWifi() {
  return yield* llamar(COM, "def _conectar_wifi", function* () {
    yield* L(COM, "self.wlan.active(True)");
    yield* L(COM, "if self.wlan.isconnected():");
    if (HW.asociado) { yield* L(COM, "return True", { en: "def _conectar_wifi" }); return true; }
    yield* L(COM, "print(\"WiFi: conectando a\""); yield serial(`WiFi: conectando a ${CFG.WIFI_SSID} ...`);
    yield* L(COM, "self.wlan.connect(self.ssid, self.clave)");
    if (HW.wifi) HW.asociadoEn = HW.t + 1200;
    yield* L(COM, "inicio = time.ticks_ms()", { en: "def _conectar_wifi" });
    const inicio = ticks();
    FW.bloqueado = true;
    while (true) {
      yield* L(COM, "while not self.wlan.isconnected():", { rapido: true });
      if (HW.asociado) break;
      yield* L(COM, "if time.ticks_diff(time.ticks_ms(), inicio) > self.wifi_timeout_ms:", { rapido: true });
      if (diff(ticks(), inicio) > CFG.WIFI_TIMEOUT_MS) {
        yield* L(COM, "print(\"WiFi: no se pudo conectar\")"); yield serial("WiFi: no se pudo conectar");
        yield* L(COM, "return False", { en: "print(\"WiFi: no se pudo conectar\")" });
        FW.bloqueado = false; HW.asociadoEn = null;
        return false;
      }
      yield* L(COM, "time.sleep_ms(200)", { rapido: true });
      yield* dormir(200);
    }
    FW.bloqueado = false;
    yield* L(COM, "print(\"WiFi: conectado, IP\""); yield serial("WiFi: conectado, IP 10.10.0.2");
    yield* L(COM, "return True", { en: "print(\"WiFi: conectado, IP\"" });
    return true;
  });
}
function* mqttConectar() {
  return yield* llamar(COM, "def conectar", function* () {
    yield* L(COM, "self.ultimo_intento = time.ticks_ms()", { en: "def conectar" }); FW.mqtt.ultimo_intento = ticks();
    yield* L(COM, "try:", { en: "def conectar" });
    yield* L(COM, "if not self._conectar_wifi():");
    if (!(yield* conectarWifi())) { yield* L(COM, "return False", { en: "if not self._conectar_wifi():" }); return false; }
    yield* L(COM, "self.cliente.connect()");
    avanzar(120);
    RED.socketMuerto = false; RED.sesion = true; RED.ultimaActividad = HW.t; RED.buzon = [];
    UI.paquete("esp", "broker", "CONNECT", `Last Will → ${CFG.TOPICO_CONEXION} = "desconectado" (retain)`, { control: true });
    for (let i = 0; i < 5; i++) {
      yield* L(COM, "for topico in self.topicos_comandos:");
      yield* L(COM, "self.cliente.subscribe(topico)");
      avanzar(15);
    }
    UI.paquete("esp", "broker", "SUBSCRIBE", "5 tópicos de comandos", { control: true });
    yield* L(COM, "self.cliente.publish(self.topico_conexion, b\"conectado\", retain=True)");
    RED.retenido[CFG.TOPICO_CONEXION] = "conectado";
    RED.desdeEsp(CFG.TOPICO_CONEXION, "conectado", { retain: true });
    yield* L(COM, "self.conectado = True", { en: "def conectar" }); FW.mqtt.conectado = true;
    yield* L(COM, "self.ultimo_ping = time.ticks_ms()", { en: "def conectar" }); FW.mqtt.ultimo_ping = ticks();
    yield* L(COM, "print(\"MQTT: conectado y suscrito a\""); yield serial("MQTT: conectado y suscrito a 5 tópicos");
    yield* L(COM, "return True", { en: "print(\"MQTT: conectado y suscrito a\"" });
    return true;
  });
}
function* mqttPublicar(topico, datos) {
  return yield* llamar(COM, "def publicar", function* () {
    yield* L(COM, "if not self.conectado:", { en: "def publicar" });
    if (!FW.mqtt.conectado) { yield* L(COM, "return False", { en: "def publicar" }); return false; }
    yield* L(COM, "try:", { en: "def publicar" });
    yield* L(COM, "self.cliente.publish(topico, json.dumps(datos))");
    avanzar(1.2);
    if (!HW.wifi || RED.socketMuerto) {
      RED.socketMuerto = true;
      UI.paquete("esp", "broker", topico, jsonDumps(datos), { perdido: true });
      yield* L(COM, "except OSError as e:", { en: "def publicar" });
      yield* L(COM, "print(\"MQTT: error al publicar:\""); yield serial(`MQTT: error al publicar: ${ERR_RED}`);
      yield* L(COM, "self.conectado = False", { en: "print(\"MQTT: error al publicar:\"" }); FW.mqtt.conectado = false;
      yield* L(COM, "return False", { en: "print(\"MQTT: error al publicar:\"" });
      return false;
    }
    RED.desdeEsp(topico, jsonDumps(datos));
    UI.ultimoPublish = `publicó ${topico.replace(CFG.PREFIJO + "/", "")} a los ${(HW.t / 1000).toFixed(1)} s`;
    yield* L(COM, "return True", { en: "def publicar" });
    return true;
  });
}
function* mqttRevisar() {
  return yield* llamar(COM, "def revisar", function* () {
    yield* L(COM, "ahora = time.ticks_ms()", { en: "def revisar" });
    const ahora = ticks();
    yield* L(COM, "if self.conectado:", { en: "def revisar" });
    if (FW.mqtt.conectado) {
      yield* L(COM, "try:", { en: "def revisar" });
      yield* L(COM, "self.cliente.check_msg()");
      if (!HW.wifi || RED.socketMuerto) {
        RED.socketMuerto = true;
        yield* L(COM, "except OSError as e:", { en: "def revisar" });
        yield* L(COM, "print(\"MQTT: conexión perdida:\""); yield serial(`MQTT: conexión perdida: ${ERR_RED}`);
        yield* L(COM, "self.conectado = False", { en: "print(\"MQTT: conexión perdida:\"" }); FW.mqtt.conectado = false;
        return "perdida";
      }
      let r = "sin mensajes";
      if (RED.buzon.length) {
        const msg = RED.buzon.shift();
        r = "comando";
        yield { tipo: "evento", texto: "check_msg() encontró un mensaje y llama al callback" };
        yield* llamar(COM, "def _mensaje_recibido", function* () {
          yield* L(COM, "try:", { en: "def _mensaje_recibido" });
          yield* L(COM, "self.al_recibir(topico.decode(), mensaje.decode().strip())");
          try {
            yield* procesarComando(msg.topico, msg.texto.trim());
          } catch (e) {
            if (!(e instanceof ErrorPy)) throw e;
            yield* L(COM, "except Exception as e:");
            yield* L(COM, "print(\"Comando inválido:\""); yield serial(`Comando inválido: ${e.message}`);
          }
        });
      }
      yield* L(COM, "if time.ticks_diff(ahora, self.ultimo_ping) >= self.ping_ms:");
      if (diff(ahora, FW.mqtt.ultimo_ping) >= CFG.MQTT_PING_MS) {
        yield* L(COM, "self.cliente.ping()");
        RED.ultimaActividad = HW.t;
        UI.paquete("esp", "broker", "PINGREQ", "sigo viva (keepalive)", { control: true });
        yield* L(COM, "self.ultimo_ping = ahora"); FW.mqtt.ultimo_ping = ahora;
        r = r === "comando" ? r : "ping";
      }
      return r;
    }
    yield* L(COM, "elif time.ticks_diff(ahora, self.ultimo_intento) >= self.reintento_ms:");
    if (diff(ahora, FW.mqtt.ultimo_intento) >= CFG.MQTT_REINTENTO_MS) {
      yield* L(COM, "self.conectar()", { en: "elif time.ticks_diff(ahora, self.ultimo_intento)" });
      yield* mqttConectar();
      return "reconexion";
    }
    return `desconectado: reintento en ${CFG.MQTT_REINTENTO_MS - diff(ahora, FW.mqtt.ultimo_intento)} ms`;
  });
}
class ErrorPy extends Error {}
function pyFloatParse(s) {
  if (!/^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(s.trim())) throw new ErrorPy("invalid syntax for number");
  const v = Number(s); return v;
}
function pyIntParse(s) {
  if (!/^[+-]?\d+$/.test(s.trim())) throw new ErrorPy("invalid syntax for integer with base 10");
  return parseInt(s, 10);
}
// ---- main.py: procesar_comando ----
function* procesarComando(topico, mensaje) {
  return yield* llamar(M, "def procesar_comando", function* () {
    yield* L(M, "print(\"Comando recibido:\""); yield serial(`Comando recibido: ${topico} = ${mensaje}`);
    yield* L(M, "if topico == config.TOPICO_CFG_UMBRAL:");
    if (topico === CFG.TOPICO_CFG_UMBRAL) {
      yield* L(M, "valor = float(mensaje)", { en: "if topico == config.TOPICO_CFG_UMBRAL:" });
      const valor = pyFloatParse(mensaje);
      yield* L(M, "if monitor.cambiar_umbral_celo(valor):");
      const ok = yield* llamar(A, "def cambiar_umbral_celo", function* () {
        yield* L(A, "if valor > self.umbral_alta:");
        if (valor > FW.monitor.umbral_alta) { yield* L(A, "self.umbral_celo = valor"); FW.monitor.umbral_celo = valor; yield* L(A, "return True", { en: "def cambiar_umbral_celo" }); return true; }
        yield* L(A, "return False", { en: "def cambiar_umbral_celo" }); return false;
      });
      if (ok) { yield* L(M, "print(\"Umbral de celo cambiado a\""); yield serial(`Umbral de celo cambiado a ${pyFloat(valor)}`); }
      else { yield* L(M, "print(\"Umbral rechazado"); yield serial(`Umbral rechazado: debe ser mayor que ${pyFloat(FW.monitor.umbral_alta)}`); }
      return;
    }
    yield* L(M, "elif topico == config.TOPICO_CFG_MUESTREO:");
    if (topico === CFG.TOPICO_CFG_MUESTREO) {
      yield* L(M, "valor = int(mensaje)");
      const valor = pyIntParse(mensaje);
      yield* L(M, "if valor >= 500:");
      if (valor >= 500) { yield* L(M, "intervalo_publicacion = valor", { en: "if valor >= 500:" }); FW.intervalo_publicacion = valor; yield* L(M, "print(\"Intervalo de publicación:\""); yield serial(`Intervalo de publicación: ${valor} ms`); }
      return;
    }
    yield* L(M, "elif topico == config.TOPICO_CMD_TARA:");
    if (topico === CFG.TOPICO_CMD_TARA) {
      yield* L(M, "balanza.tara()", { en: "elif topico == config.TOPICO_CMD_TARA:" });
      yield* balanzaTara();
      yield* L(M, "print(\"Tara realizada\")"); yield serial("Tara realizada");
      return;
    }
    yield* L(M, "elif topico == config.TOPICO_CMD_CALIBRAR:");
    if (topico === CFG.TOPICO_CMD_CALIBRAR) {
      yield* L(M, "peso = float(mensaje)");
      const peso = pyFloatParse(mensaje);
      yield* L(M, "if balanza.calibrar(peso):");
      if (yield* balanzaCalibrar(peso)) { yield* L(M, "print(\"Calibrada. Nuevo factor:\""); yield serial(`Calibrada. Nuevo factor: ${pyFloat(FW.balanza.factor)}`); }
      else { yield* L(M, "print(\"Calibración inválida\")"); yield serial("Calibración inválida"); }
      return;
    }
    yield* L(M, "elif topico == config.TOPICO_CMD_BUZZER:");
    if (topico === CFG.TOPICO_CMD_BUZZER) {
      yield* L(M, "if mensaje.lower() == \"silenciar\":");
      if (mensaje.toLowerCase() === "silenciar") { yield* L(M, "buzzer.silenciar(True)"); yield* buzzerSilenciar(true); }
      else {
        yield* L(M, "elif mensaje.lower() == \"activar\":");
        if (mensaje.toLowerCase() === "activar") { yield* L(M, "buzzer.silenciar(False)"); yield* buzzerSilenciar(false); }
      }
      yield* L(M, "print(\"Buzzer:\", mensaje)"); yield serial(`Buzzer: ${mensaje}`);
    }
  });
}

// ---- main.py: arranque y bucle ----
function* programa() {
  FW.fase = "arranque";
  yield { tipo: "vuelta", arranque: true };
  yield* L(M, "semaforo = Semaforo(");
  HW.led = { verde: 0, amarillo: 0, rojo: 0 };
  yield* L(M, "buzzer = Buzzer(");
  yield* L(M, "boton = Boton(");
  yield* L(M, "i2c = I2C(0");
  yield* L(M, "mpu = MPU6050(i2c)");
  yield* llamar(MPU, "def __init__", function* () {
    yield* L(MPU, "if direccion not in i2c.scan():");
    HW.i2cFlash = performance.now();
    yield* L(MPU, "self.i2c.writeto_mem(direccion, self.REG_PWR_MGMT_1, b\"\\x00\")");
    yield* L(MPU, "self.i2c.writeto_mem(direccion, self.REG_ACCEL_CONFIG, b\"\\x00\")");
  });
  yield* L(M, "monitor = MonitorActividad(", { n: 8 });
  yield* L(M, "balanza = Balanza(", { n: 7 });
  yield* L(M, "try:", { en: "balanza = Balanza(" });
  yield* L(M, "balanza.tara()          # La balanza");
  yield* balanzaTara();
  yield* L(M, "print(\"Balanza: tara lista\")"); yield serial("Balanza: tara lista");
  yield* L(M, "registros = []"); FW.registros = [];
  yield* L(M, "intervalo_publicacion = config.INTERVALO_PUBLICACION_MS");
  yield* L(M, "mqtt = ClienteMQTT(", { n: 10 });
  yield* L(M, "mqtt.conectar()");
  yield* mqttConectar();
  yield* L(M, "semaforo.mostrar(config.ESTADO_NORMAL)");
  yield* semaforoMostrar(CFG.ESTADO_NORMAL);
  yield* L(M, "segundos = config.VENTANA_ACTIVIDAD_MS");
  const segundos = Math.floor(CFG.VENTANA_ACTIVIDAD_MS * CFG.VENTANAS_CALIBRACION / 1000);
  yield* L(M, "print(\"Calibrando actividad durante\""); yield serial(`Calibrando actividad durante ${segundos} s. Mantén el sensor quieto...`);
  yield* L(M, "ultima_lectura_mpu = time.ticks_ms()"); FW.ultima_lectura_mpu = ticks();
  yield* L(M, "ultima_publicacion_peso = time.ticks_ms()"); FW.ultima_publicacion_peso = ticks();
  yield* L(M, "monitor.inicio_ventana = time.ticks_ms()"); FW.monitor.inicio_ventana = ticks();
  FW.fase = "bucle";
  while (true) {
    yield { tipo: "vuelta" };
    yield* L(M, "while True:");
    yield* L(M, "ahora = time.ticks_ms()", { en: "while True:" });
    FW.ahora = ticks();
    const ahora = FW.ahora;
    // Tarea 1
    yield* L(M, "if time.ticks_diff(ahora, ultima_lectura_mpu) >= config.INTERVALO_LECTURA_MPU_MS:");
    const d1 = diff(ahora, FW.ultima_lectura_mpu);
    if (d1 >= CFG.INTERVALO_LECTURA_MPU_MS) {
      yield tarea(1, "corre", `pasaron ${d1} ms`);
      yield* L(M, "ultima_lectura_mpu = ahora", { en: "# Tarea 1" }); FW.ultima_lectura_mpu = ahora;
      yield* L(M, "try:", { en: "# Tarea 1" });
      yield* L(M, "ax, ay, az = mpu.leer_aceleracion()");
      const [ax, ay, az] = yield* leerAceleracion();
      FW.ax = ax; FW.ay = ay; FW.az = az;
      yield* L(M, "monitor.agregar_muestra(ax, ay, az)");
      yield* agregarMuestra(ax, ay, az);
    } else yield tarea(1, "salta", `faltan ${CFG.INTERVALO_LECTURA_MPU_MS - d1} ms`);
    // Tarea 2
    yield* L(M, "balanza.actualizar()", { en: "# Tarea 2" });
    const leyo = yield* balanzaActualizar();
    yield tarea(2, leyo ? "corre" : "nada", leyo ? "leyó un dato nuevo del HX711" : "sin dato listo (DT = 1)");
    // Tarea 3
    yield* L(M, "if monitor.actualizar():");
    const nueva = yield* monitorActualizar();
    if (nueva) {
      yield tarea(3, "corre", "terminó la ventana de 10 s");
      const m = FW.monitor;
      yield* L(M, "if monitor.calibrando:");
      if (m.calibrando) {
        yield* L(M, "print(\"Calibrando... ventana\"", { n: 2 }); yield serial(`Calibrando... ventana ${m.ventanas_calibradas} de ${CFG.VENTANAS_CALIBRACION}`);
      } else {
        yield* L(M, "print(\"[Vaca] Actividad:", { n: 2 });
        yield serial(`[Vaca] Actividad: ${fmt(m.actividad, 4)} g | Base: ${fmt(m.linea_base, 4)} g | Razón: ${fmt(m.razon, 2)} | ${m.estado}`);
        yield* L(M, "semaforo.mostrar(monitor.estado)");
        yield* semaforoMostrar(m.estado);
        yield* L(M, "if monitor.estado == config.ESTADO_CELO:");
        if (m.estado === CFG.ESTADO_CELO) { yield* L(M, "buzzer.activar()"); yield* buzzerActivar(); }
        else { yield* L(M, "buzzer.desactivar()"); yield* buzzerDesactivar(); }
        yield* L(M, "mqtt.publicar(config.TOPICO_ACTIVIDAD, {", { n: 5 });
        yield* mqttPublicar(CFG.TOPICO_ACTIVIDAD, { actividad: F(redondear(m.actividad, 4)), linea_base: F(redondear(m.linea_base, 4)), razon: F(redondear(m.razon, 2)) });
        yield* L(M, "mqtt.publicar(config.TOPICO_ESTADO, {", { n: 4 });
        yield* mqttPublicar(CFG.TOPICO_ESTADO, { estado: m.estado, umbral: F(m.umbral_celo) });
      }
    } else yield tarea(3, "salta", `faltan ${CFG.VENTANA_ACTIVIDAD_MS - diff(ticks(), FW.monitor.inicio_ventana)} ms para cerrar la ventana`);
    // Tarea 4
    yield* L(M, "if time.ticks_diff(ahora, ultima_publicacion_peso) >= intervalo_publicacion:");
    const d4 = diff(ahora, FW.ultima_publicacion_peso);
    if (d4 >= FW.intervalo_publicacion) {
      yield tarea(4, "corre", `pasaron ${d4} ms`);
      yield* L(M, "ultima_publicacion_peso = ahora", { en: "# Tarea 4" }); FW.ultima_publicacion_peso = ahora;
      yield* L(M, "estable = balanza.es_estable()");
      const estable = yield* balanzaEsEstable(); FW.estable = estable;
      yield* L(M, "print(\"[Leche]", { n: 2 }); yield serial(`[Leche] ${fmt(pesoKg(), 2)} kg | ${fmt(litros(), 2)} L | ${estable ? "estable" : "moviéndose"}`);
      yield* L(M, "mqtt.publicar(config.TOPICO_PESO, {", { n: 5 });
      yield* mqttPublicar(CFG.TOPICO_PESO, { kg: F(redondear(pesoKg(), 2)), litros: F(redondear(litros(), 2)), estable });
    } else yield tarea(4, "salta", `faltan ${FW.intervalo_publicacion - d4} ms`);
    // Tarea 5
    yield* L(M, "if boton.fue_presionado():");
    const p = yield* botonFuePresionado();
    if (p.r) {
      yield tarea(5, "corre", "¡pulsación confirmada!");
      yield* L(M, "if balanza.es_estable() and balanza.litros() > 0:");
      const ok = (yield* balanzaEsEstable()) && litros() > 0;
      if (ok) {
        yield* L(M, "litros = balanza.litros()"); const lt = litros();
        yield* L(M, "registros.append(litros)"); FW.registros.push(lt);
        const total = FW.registros.reduce((a, b) => a + b, 0);
        yield* L(M, "print(\">>> Ordeño #", { n: 2 }); yield serial(`>>> Ordeño #${FW.registros.length} registrado: ${fmt(lt, 2)} L | Total: ${fmt(total, 2)} L`);
        yield* L(M, "mqtt.publicar(config.TOPICO_REGISTRO, {", { n: 5 });
        yield* mqttPublicar(CFG.TOPICO_REGISTRO, { ordeno: FW.registros.length, litros: F(redondear(lt, 2)), total: F(redondear(total, 2)) });
      } else {
        yield* L(M, "print(\">>> No se registró"); yield serial(">>> No se registró: el peso no está estable o la balanza está vacía");
      }
    } else yield tarea(5, "nada", p.motivo);
    // Tarea 6
    yield* L(M, "mqtt.revisar()");
    const rv = yield* mqttRevisar();
    yield tarea(6, rv === "sin mensajes" ? "nada" : "corre", rv === "sin mensajes" ? "check_msg(): no llegó nada" : rv === "comando" ? "llegó un comando" : rv === "ping" ? "envió PINGREQ" : rv === "perdida" ? "se detectó la caída" : rv === "reconexion" ? "intentó reconectar" : rv);
    // Tarea 7
    yield* L(M, "buzzer.actualizar()");
    const bz = yield* buzzerActualizar();
    yield tarea(7, bz === "cambio" ? "corre" : "nada", bz === "cambio" ? (FW.buzzer.sonando ? "tono ON" : "tono OFF") : typeof bz === "number" ? `faltan ${bz} ms para cambiar el tono` : bz === "silenciado" ? "alarma silenciada" : "buzzer inactivo");
    yield* L(M, "time.sleep_ms(5)", { en: "# Tarea 7" });
    avanzar(0.35);                    // tiempo de ejecución del propio bucle
    yield* dormir(5);
  }
}

// ======================================================================
// 6. Motor: ejecuta el generador en modo continuo, lento o paso a paso
// ======================================================================
const MOTOR = {
  gen: null, velocidad: 1, modo: "pausa", // continuo | pausa | lento
  pendiente: null,                          // evento ya sacado pero no procesado
  vuelta: [], tareas: {}, pila: [], vueltaN: 0,
  ultimaVista: null, vistaHasta: 0,
  lentoCada: 520, lentoFin: null, lentoTimer: 0, cond: null, alCumplir: null,
  reiniciar() {
    semilla = 7;
    Object.assign(HW, { t: 0, ax: 0, ay: 0, az: 1, kg: 0, kgObjetivo: 0, oleaje: 0, hxListo: false, hxProx: 100, hxUltimo: null, botonAbajo: false, botonCambio: -1e9, botonSoltarEn: null, asociado: false, asociadoEn: null, led: { verde: 0, amarillo: 0, rojo: 0 }, pwm: 0 });
    Object.assign(RED, { sesion: false, ultimaActividad: 0, buzon: [], socketMuerto: false, app: {} });
    RED.retenido[CFG.TOPICO_CONEXION] = null;
    reiniciarFW();
    this.gen = programa(); this.pendiente = null; this.vuelta = []; this.tareas = {}; this.pila = []; this.vueltaN = 0;
    this.ultimaVista = null;
    UI.limpiar();
  },
  // procesa un evento; devuelve true si consumió tiempo
  procesar(ev) {
    switch (ev.tipo) {
      case "vuelta":
        if (this.vuelta.length) this.cerrarVuelta();
        this.vuelta = []; this.tareas = {}; this.vueltaN++;
        return false;
      case "linea": this.vuelta.push(ev); return false;
      case "entrar": this.pila.push(ev); this.vuelta.push(ev); return false;
      case "salir": this.pila.pop(); this.vuelta.push(ev); return false;
      case "tarea": this.tareas[ev.n] = ev; return false;
      case "print": this.vuelta.push(ev); return false;
      case "evento": this.vuelta.push(ev); return false;
      case "dormir": avanzar(ev.ms); return true;
    }
    return false;
  },
  siguiente() {
    if (this.pendiente) { const e = this.pendiente; this.pendiente = null; return e; }
    const r = this.gen.next();
    return r.value;
  },
  cerrarVuelta() {
    const v = { lineas: this.vuelta, tareas: this.tareas, n: this.vueltaN, t: HW.t };
    let puntaje = 0;
    for (const e of v.lineas) { if (e.tipo === "print") puntaje = Math.max(puntaje, 3); if (e.tipo === "entrar" && (e.def.includes("publicar") || e.def.includes("_mensaje"))) puntaje = Math.max(puntaje, 3); }
    if (puntaje < 2 && v.tareas[1] && v.tareas[1].estado === "corre") puntaje = 1;
    if (puntaje < 2 && v.tareas[2] && v.tareas[2].estado === "corre") puntaje = Math.max(puntaje, 1);
    v.puntaje = puntaje;
    const ahora = performance.now();
    if (!this.ultimaVista || ahora >= this.vistaHasta || puntaje > this.ultimaVista.puntaje) {
      this.ultimaVista = v;
      this.vistaHasta = ahora + (puntaje >= 3 ? 1600 : puntaje >= 1 ? 260 : 90);
      UI.mostrarVuelta(v);
    }
  },
  // modo continuo: corre hasta el tiempo virtual objetivo
  correrHasta(tObjetivo, limite = 60000) {
    let n = 0;
    while (HW.t < tObjetivo && n++ < limite) {
      const ev = this.siguiente();
      if (ev.tipo === "vuelta" && this.cond && this.cond()) { this.pendiente = ev; this.cumplir(); return; }
      this.procesar(ev);
      if (FW.bloqueado && ev.tipo === "dormir") UI.bloqueo(true);
    }
  },
  cumplir() { const f = this.alCumplir; this.cond = null; this.alCumplir = null; if (f) f(); },
  // modo lento: una línea por intervalo, cambiando de pestaña
  pasoLento() {
    while (true) {
      const ev = this.siguiente();
      if (ev.tipo === "vuelta" && this.lentoFin === "vuelta" && this.vuelta.length && this.lentoArranco) {
        this.pendiente = ev; this.lentoArranco = false; this.parar(); return;
      }
      this.lentoArranco = true;
      this.procesar(ev);
      if (ev.tipo === "linea") { const e = esperaLinea(ev, 90, this.lentoCada); if (e > 5 || RAPIDOS.n % 9 === 0) UI.lineaActual(ev); return e; }
      if (ev.tipo === "tarea") UI.tareaVivo(ev);
      if (ev.tipo === "print") { UI.lineaPrint(); }
      if (ev.tipo === "evento") { UI.nota(ev.texto); return this.lentoCada; }
      if (ev.tipo === "dormir") { UI.refrescar(); if (FW.bloqueado) return 30; }
      if (this.lentoFin === "condicion" && ev.tipo === "vuelta" && this.cond && this.cond()) { /* no usado */ }
    }
  },
  lento(fin = "vuelta", cada = 520) {
    this.modo = "lento"; this.lentoFin = fin; this.lentoCada = cada; this.lentoArranco = false;
    clearTimeout(this.lentoTimer);
    const tic = () => {
      if (this.modo !== "lento") return;
      const espera = this.pasoLento();
      if (this.modo === "lento") this.lentoTimer = setTimeout(tic, espera);
    };
    tic();
  },
  parar() {
    this.modo = "pausa"; clearTimeout(this.lentoTimer);
    UI.estadoMotor();
    if (this.alParar) { const f = this.alParar; this.alParar = null; f(); }
  },
  continuo() { clearTimeout(this.lentoTimer); this.modo = "continuo"; UI.limpiarActual(); UI.estadoMotor(); },
};

const RAPIDOS = { n: 0 };
function esperaLinea(ev, rapida, normal) {
  if (!ev.rapido) { RAPIDOS.n = 0; return normal; }
  RAPIDOS.n++;
  return RAPIDOS.n <= 12 ? rapida : 3;
}

// ======================================================================
// 7. Interfaz
// ======================================================================
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const NOMBRES = ["main.py", "actividad.py", "balanza.py", "hx711.py", "indicadores.py", "boton.py", "mpu6050.py", "comunicacion.py", "config.py"];
const TAREAS_LINEA = {};
for (let n = 1; n <= 7; n++) TAREAS_LINEA[n] = lineaDe(M, `# Tarea ${n}:`, "while True:");
const NOMBRE_TAREA = { 1: "Tarea 1 · acelerómetro", 2: "Tarea 2 · balanza", 3: "Tarea 3 · ventana de actividad", 4: "Tarea 4 · publicar peso", 5: "Tarea 5 · pulsador", 6: "Tarea 6 · MQTT", 7: "Tarea 7 · buzzer" };

const UI = {
  archivo: "main.py", seguir: true, ultimoPrint: null,
  init() {
    this.svg = $(".escena svg");
    this.tooltip = $("#tooltip");
    // código
    const tabs = $("#tabs");
    tabs.innerHTML = NOMBRES.map((f) => `<button class="tab" data-f="${f}">${f}<i></i></button>`).join("");
    tabs.addEventListener("click", (e) => { const b = e.target.closest(".tab"); if (b) { this.verArchivo(b.dataset.f, true); } });
    const codigo = $("#codigo");
    codigo.innerHTML = NOMBRES.map((f) => `<pre class="archivo" data-f="${f}">${LINEAS[f].map((l, i) => `<span class="ln" data-l="${i + 1}"><b>${i + 1}</b>${resaltarPy(l) || " "}</span>`).join("")}</pre>`).join("");
    for (let n = 1; n <= 7; n++) {
      const ln = $(`.archivo[data-f="main.py"] .ln[data-l="${TAREAS_LINEA[n]}"]`);
      ln.classList.add("tarea-cab"); ln.insertAdjacentHTML("beforeend", `<em class="insignia" data-t="${n}"></em>`);
    }
    this.verArchivo("main.py");
    // tareas
    $("#tareas").innerHTML = [1, 2, 3, 4, 5, 6, 7].map((n) => `<li data-t="${n}"><b>${n}</b><span>${NOMBRE_TAREA[n].split(" · ")[1]}</span><em></em></li>`).join("");
    $("#tareas").addEventListener("click", (e) => { const li = e.target.closest("li"); if (li) { this.verArchivo("main.py", true); this.scrollA(TAREAS_LINEA[li.dataset.t], true); } });
    if (erroresLinea.length) { $("#errores").hidden = false; $("#errores").textContent = "Líneas no encontradas en el código: " + erroresLinea.join(" · "); }
    this.cables();
    this.construirRed();
  },
  verArchivo(f, manual) {
    this.archivo = f;
    $$(".archivo").forEach((p) => p.classList.toggle("visible", p.dataset.f === f));
    $$(".tab").forEach((t) => t.classList.toggle("activa", t.dataset.f === f));
    if (manual) this.manualHasta = performance.now() + 6000;
  },
  scrollA(l, forzar) {
    const ln = $(`.archivo[data-f="${this.archivo}"] .ln[data-l="${l}"]`);
    if (!ln) return;
    const caja = $("#codigo");
    const top = ln.offsetTop - caja.clientHeight * 0.38;
    if (forzar || Math.abs(caja.scrollTop - top) > caja.clientHeight * 0.3) caja.scrollTo({ top, behavior: "auto" });
  },
  limpiarActual() { $$(".ln.actual").forEach((x) => x.classList.remove("actual")); $("#nota").textContent = ""; },
  // modo lento: resaltar UNA línea y seguirla entre archivos
  lineaActual(ev) {
    $$(".ln.actual").forEach((x) => x.classList.remove("actual"));
    $$(".ln.corrio").forEach((x) => x.classList.remove("corrio"));
    if (this.archivo !== ev.f) this.verArchivo(ev.f);
    for (let i = 0; i < ev.n; i++) $(`.archivo[data-f="${ev.f}"] .ln[data-l="${ev.l + i}"]`)?.classList.add("actual");
    this.scrollA(ev.l, true);
    this.marcarPila();
    if (ev.nota) this.nota(ev.nota); else if (!ev.rapido) this.nota("");
    this.refrescar();
  },
  nota(t) { $("#nota").textContent = t; },
  lineaPrint() { this.refrescar(); },
  marcarPila() {
    const pila = MOTOR.pila.map((e) => `${e.f}:${e.def.replace("def ", "")}()`);
    $("#pila").textContent = pila.length ? "main.py → " + pila.join(" → ") : "main.py";
    const activos = new Set(MOTOR.pila.map((e) => e.f));
    $$(".tab").forEach((t) => t.classList.toggle("en-pila", activos.has(t.dataset.f)));
  },
  tareaVivo(ev) {
    const li = $(`#tareas li[data-t="${ev.n}"]`);
    li.dataset.estado = ev.estado; li.querySelector("em").textContent = ev.motivo || "";
    const ins = $(`.insignia[data-t="${ev.n}"]`);
    ins.dataset.estado = ev.estado; ins.textContent = ev.estado === "salta" ? `se salta: ${ev.motivo}` : ev.motivo;
  },
  // modo continuo: mostrar la vuelta elegida completa
  mostrarVuelta(v) {
    $$(".ln.corrio").forEach((x) => x.classList.remove("corrio"));
    $$(".tab").forEach((t) => t.classList.remove("toco"));
    let foco = null;
    for (const e of v.lineas) {
      if (e.tipo === "linea" && e.f === "main.py") { for (let i = 0; i < e.n; i++) $(`.archivo[data-f="main.py"] .ln[data-l="${e.l + i}"]`)?.classList.add("corrio"); }
      if (e.tipo === "linea" && e.f !== "main.py") { $(`.archivo[data-f="${e.f}"] .ln[data-l="${e.l}"]`)?.classList.add("corrio"); $(`.tab[data-f="${e.f}"]`).classList.add("toco"); }
      if (e.tipo === "linea" && e.f === "main.py" && v.puntaje >= 1 && !/while True|ahora = time|time.sleep_ms|^if time|balanza.actualizar|mqtt.revisar|buzzer.actualizar|if boton|if monitor.actualizar/.test(LINEAS["main.py"][e.l - 1].trim())) foco = e.l;
    }
    for (let n = 1; n <= 7; n++) if (v.tareas[n]) this.tareaVivo(v.tareas[n]);
    if (this.archivo === "main.py" && !(performance.now() < (this.manualHasta || 0))) this.scrollA(foco || lineaDe(M, "while True:"));
    if (!(performance.now() < (this.manualHasta || 0)) && this.archivo !== "main.py") this.verArchivo("main.py");
  },
  serial(texto, clase) {
    const s = $("#serial");
    const linea = document.createElement("div");
    linea.textContent = texto;
    linea.className = "nuevo";
    if (/^\[Vaca\]/.test(texto)) linea.dataset.k = texto.includes(CFG.ESTADO_CELO) ? "celo" : texto.includes(CFG.ESTADO_ALTA) ? "alta" : "vaca";
    if (/^>>>/.test(texto)) linea.dataset.k = texto.includes("No se") ? "error" : "ordeno";
    if (/error|perdida|no se pudo|inválid|rechazad/i.test(texto)) linea.dataset.k = "error";
    if (/^(WiFi|MQTT): con/.test(texto)) linea.dataset.k = "red";
    if (clase) linea.dataset.k = clase;
    const tt = document.createElement("span"); tt.className = "t"; tt.textContent = (HW.t / 1000).toFixed(2).padStart(7, " ") + " s ";
    linea.prepend(tt);
    s.appendChild(linea);
    while (s.children.length > 300) s.firstChild.remove();
    s.scrollTop = s.scrollHeight;
    setTimeout(() => linea.classList.remove("nuevo"), 1600);
  },
  limpiar() { this.gen = (this.gen || 0) + 1; this.enVuelo = 0; $("#serial").innerHTML = ""; $$(".ln.corrio,.ln.actual").forEach((x) => x.classList.remove("corrio", "actual")); $("#paquetes").innerHTML = ""; this.appReset(); },
  estadoMotor() {
    $("#btn-pausa").textContent = MOTOR.modo === "continuo" ? "⏸ Pausa" : "▶ Continuar";
    document.body.dataset.modo = MOTOR.modo;
    $$("[data-vel]").forEach((b) => b.classList.toggle("activa", Number(b.dataset.vel) === MOTOR.velocidad && MOTOR.modo === "continuo"));
  },
  bloqueo(si) { document.body.classList.toggle("bloqueada", si); },
  boton(abajo) { this.svg.querySelector('[data-part="boton-tapa"]').setAttribute("transform", abajo ? translateAlong(ESCENA.P, [0, 0, -2.4]) : ""); },

  // --- cables y ayudas ---
  cables() {
    const info = Object.fromEntries(ESCENA.CABLES.map((c) => [c.id, c.info]));
    info.mpu = { pin: "GPIO 21 / 22 + 3V3 / GND", que: "Cable del collar al MPU6050", proto: "Bus I2C: SDA 21, SCL 22, 400 kHz, dirección 0x68", cfg: "PIN_I2C_SDA = 21 · PIN_I2C_SCL = 22" };
    for (const w of ["E+", "E−", "A−", "A+"]) info["celda-" + w] = { pin: w, que: "Celda de carga → HX711", proto: w.startsWith("E") ? "Excitación del puente de Wheatstone" : "Señal diferencial (milivoltios)", cfg: "" };
    this.svg.addEventListener("pointermove", (e) => {
      const g = e.target.closest("[data-cable]");
      $$(".cable.hover").forEach((x) => x !== g && x.classList.remove("hover"));
      if (!g) { this.tooltip.hidden = true; return; }
      g.classList.add("hover");
      const i = info[g.dataset.cable];
      this.tooltip.hidden = false;
      this.tooltip.innerHTML = `<b>${i.pin}</b><span>${i.que}</span><span>${i.proto}</span>${i.cfg ? `<code>${i.cfg}</code>` : ""}`;
      const r = $(".escena").getBoundingClientRect();
      this.tooltip.style.left = Math.min(r.width - 330, e.clientX - r.left + 14) + "px";
      this.tooltip.style.top = (e.clientY - r.top + 16) + "px";
    });
    this.svg.addEventListener("pointerleave", () => { this.tooltip.hidden = true; });
    const tapa = this.svg.querySelector('[data-part="boton-tapa"]');
    tapa.addEventListener("pointerdown", (e) => { e.preventDefault(); presionarBoton(); });
    window.addEventListener("pointerup", () => soltarBoton(false));
  },

  // --- red: ESP32 ⇄ broker ⇄ app ---
  construirRed() { this.appReset(); },
  appReset() {
    const etiquetas = { [CFG.TOPICO_CONEXION]: "conexion", [CFG.TOPICO_ESTADO]: "estado", [CFG.TOPICO_ACTIVIDAD]: "actividad", [CFG.TOPICO_PESO]: "peso", [CFG.TOPICO_REGISTRO]: "registro" };
    $("#app-datos").innerHTML = Object.entries(etiquetas).map(([t, n]) => `<div data-topico="${t}"><span>${n}</span><code>—</code></div>`).join("");
  },
  app(topico, texto) {
    const d = $(`#app-datos [data-topico="${topico}"]`);
    if (!d) return;
    d.querySelector("code").textContent = texto;
    d.classList.remove("flash"); void d.offsetWidth; d.classList.add("flash");
  },
  log(quien, texto) { this.serialRed(texto); },
  serialRed(texto) { const el = $("#broker-log"); el.textContent = texto; el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash"); },
  enVuelo: 0,
  paquete(de, a, topico, texto, op = {}) {
    const cont = $("#paquetes");
    if (this.enVuelo > 6 && !op.control && !op.will && !op.llega) { if (op.siguiente) op.siguiente(); return; }
    const x = { esp: 0.035, broker: 0.5, app: 0.965 };
    const el = document.createElement("div");
    el.className = "paquete" + (op.perdido ? " perdido" : "") + (op.control ? " control" : "") + (op.will ? " will" : "") + (de === "app" || de === "broker" && a === "esp" ? " baja" : "");
    const corto = topico.replace(CFG.PREFIJO + "/", "");
    el.innerHTML = `<b>${corto}</b><code>${escaparHtml(texto)}</code>`;
    cont.appendChild(el);
    this.enVuelo++;
    const dur = 1100;
    const t0 = performance.now(), gen = this.gen || 0;
    const x0 = x[de], x1 = op.perdido ? (x[de] + x[a]) / 2 : x[a];
    const w = cont.clientWidth;
    const mover = (now) => {
      const p = Math.min(1, (now - t0) / dur);
      const e = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;
      const mitad = el.offsetWidth / 2 + 2;
      el.style.left = Math.max(mitad, Math.min(w - mitad, (x0 + (x1 - x0) * e) * w)) + "px";
      el.style.opacity = op.perdido ? String(1 - p * 0.9) : p > 0.92 ? String((1 - p) / 0.08) : "1";
      if (p < 1) requestAnimationFrame(mover);
      else {
        el.remove(); this.enVuelo = Math.max(0, this.enVuelo - 1);
        if (gen !== (this.gen || 0)) return;   // paquete de antes de reiniciar
        if (op.perdido) this.serialRed("✗ Sin WiFi: el paquete no sale de la ESP32");
        if (op.siguiente) this.paquete("broker", "app", topico, texto, { llega: op.siguiente });
        else if (op.llega) op.llega();
        if (de === "esp" && a === "broker" && !op.perdido && !op.control) this.serialRed(`Broker recibió ${corto}`);
        if (op.will) { RED.app[topico] = texto; this.app(topico, texto); }
        if (topico === CFG.TOPICO_CONEXION && a === "broker" && !op.perdido) { /* retenido */ }
      }
    };
    requestAnimationFrame(mover);
  },
  hxZoom(u) { HXZ.dibujar(u); },

  // --- dibujo por cuadro de la escena y variables ---
  refrescar() { ESC.dibujar(); VAR.dibujar(); },
};
function escaparHtml(s) { return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }

// Resaltado de sintaxis mínimo de Python (tokenizador)
const PALABRAS = new Set("def class if elif else while for in return try except import from as not and or global True False None is with pass break continue lambda".split(" "));
function resaltarPy(l) {
  const re = /("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|(#.*$)|(\b0x[0-9A-Fa-f]+\b|\b\d+\.?\d*\b)|([A-Za-z_][A-Za-z0-9_]*)|([^"'#A-Za-z0-9_]+|.)/g;
  let out = "", m;
  while ((m = re.exec(l))) {
    const t = escaparHtml(m[0]);
    if (m[1]) out += `<s class="c">${t}</s>`;
    else if (m[2]) out += `<s class="m">${t}</s>`;
    else if (m[3]) out += `<s class="n">${t}</s>`;
    else if (m[4]) out += PALABRAS.has(m[4]) ? `<s class="k">${t}</s>` : t;
    else out += t;
    if (m[0] === "") re.lastIndex++;
  }
  return out;
}

// Variables en vivo
const VAR = {
  prev: {},
  filas: [
    ["ahora", () => FW.ahora + " ms"],
    ["ultima_lectura_mpu", () => FW.ultima_lectura_mpu + " ms"],
    ["ax, ay, az", () => `${FW.ax.toFixed(3)}, ${FW.ay.toFixed(3)}, ${FW.az.toFixed(3)} g`],
    ["monitor.suma", () => FW.monitor.suma.toFixed(4)],
    ["monitor.muestras", () => String(FW.monitor.muestras)],
    ["monitor.actividad", () => FW.monitor.actividad.toFixed(4) + " g"],
    ["monitor.linea_base", () => FW.monitor.linea_base.toFixed(4) + " g"],
    ["monitor.razon", () => FW.monitor.razon.toFixed(2)],
    ["monitor.estado", () => `"${FW.monitor.estado}"`],
    ["monitor.calibrando", () => pyVal(FW.monitor.calibrando) + (FW.monitor.calibrando ? ` (${FW.monitor.ventanas_calibradas}/${CFG.VENTANAS_CALIBRACION})` : "")],
    ["monitor.umbral_celo", () => pyFloat(FW.monitor.umbral_celo)],
    ["balanza.lecturas", () => "[" + FW.balanza.lecturas.map((v) => v.toFixed(3)).join(", ") + "]"],
    ["balanza.peso_kg()", () => pesoKg().toFixed(3) + " kg"],
    ["balanza.litros()", () => litros().toFixed(3) + " L"],
    ["balanza.es_estable()", () => pyVal(esEstable()) + (FW.balanza.lecturas.length === CFG.MUESTRAS_ESTABILIDAD ? `  (Δ ${((Math.max(...FW.balanza.lecturas) - Math.min(...FW.balanza.lecturas)) * 1000).toFixed(0)} g)` : "")],
    ["balanza.factor", () => pyFloat(FW.balanza.factor)],
    ["intervalo_publicacion", () => FW.intervalo_publicacion + " ms"],
    ["buzzer.activo / silenciado", () => `${pyVal(FW.buzzer.activo)} / ${pyVal(FW.buzzer.silenciado)}`],
    ["mqtt.conectado", () => pyVal(FW.mqtt.conectado)],
    ["registros", () => "[" + FW.registros.map((v) => v.toFixed(2)).join(", ") + "]"],
  ],
  init() {
    $("#vars").innerHTML = this.filas.map(([n], i) => `<div class="var" data-i="${i}"><span>${n}</span><code></code></div>`).join("");
    this.celdas = $$("#vars .var code");
    this.filasEl = $$("#vars .var");
  },
  dibujar() {
    const ahora = performance.now();
    this.filas.forEach(([n, f], i) => {
      const v = f();
      if (this.prev[n] !== v) {
        this.celdas[i].textContent = v;
        if (this.prev[n] !== undefined && n !== "ahora") { this.filasEl[i].classList.add("cambio"); this.filasEl[i].dataset.hasta = ahora + 900; }
        this.prev[n] = v;
      } else if (this.filasEl[i].dataset.hasta && ahora > Number(this.filasEl[i].dataset.hasta)) { this.filasEl[i].classList.remove("cambio"); delete this.filasEl[i].dataset.hasta; }
    });
    const estados = { [CFG.ESTADO_NORMAL]: "normal", [CFG.ESTADO_ALTA]: "alta", [CFG.ESTADO_CELO]: "celo" };
    $("#lectura-estado").dataset.e = FW.monitor.calibrando ? "cal" : estados[FW.monitor.estado];
    $("#lectura-estado").textContent = FW.monitor.calibrando ? `calibrando ${FW.monitor.ventanas_calibradas}/${CFG.VENTANAS_CALIBRACION}` : FW.monitor.estado;
    $("#lectura-razon").textContent = FW.monitor.calibrando ? "—" : FW.monitor.razon.toFixed(2);
    $("#lectura-litros").textContent = litros().toFixed(2) + " L";
    $("#lectura-reloj").textContent = (HW.t / 1000).toFixed(1) + " s";
    const ventana = Math.min(1, (ticks() - FW.monitor.inicio_ventana) / CFG.VENTANA_ACTIVIDAD_MS);
    $("#barra-ventana").style.width = (FW.fase === "bucle" ? ventana * 100 : 0) + "%";
    $("#ventana-txt").textContent = FW.fase === "bucle" ? `${((ticks() - FW.monitor.inicio_ventana) / 1000).toFixed(1)} / 10 s · ${FW.monitor.muestras} muestras` : "arranque";
    $("#red-esp").dataset.ok = FW.mqtt.conectado ? "1" : "0";
    $("#red-broker").dataset.sesion = RED.sesion ? "1" : "0";
    $("#red-esp-estado").textContent = FW.mqtt.conectado ? "mqtt.conectado = True" : FW.bloqueado ? "bloqueada en _conectar_wifi()" : "mqtt.conectado = False";
    $("#red-esp-ultimo").textContent = UI.ultimoPublish || "";
    $("#broker-estado").textContent = RED.sesion ? "sesión abierta" : "sin sesión";
    $("#broker-retenido").textContent = `conexion (retain) = ${RED.retenido[CFG.TOPICO_CONEXION] ?? "—"}`;
    const k = HW.t - RED.ultimaActividad;
    $("#broker-keep").textContent = RED.sesion ? `última noticia hace ${(k / 1000).toFixed(0)} s (corta a los ${1.5 * CFG.MQTT_KEEPALIVE_S} s)` : "";
  },
};

// Escena: piezas que se mueven
const ESC = {
  init() {
    const s = UI.svg;
    this.cabeza = s.querySelector('[data-part="cabeza"]');
    this.plato = s.querySelector('[data-part="plato"]');
    this.leche = s.querySelector('[data-part="leche"]');
    this.chorro = s.querySelector('[data-part="chorro"]');
    this.ondas = s.querySelector('[data-part="ondas"]');
    this.wifi = s.querySelector('[data-part="wifi"]');
    this.mazo = ["a", "b", "c", "d"].map((x) => s.querySelector(`[data-part="mazo-${x}"]`));
    this.leds = Object.fromEntries(["verde", "amarillo", "rojo"].map((n) => [n, s.querySelector(`[data-led="${n}"]`)]));
    this.cab = { y: 0, z: 0 };
    // ondas del buzzer y del WiFi (arcos en pantalla)
    const [bx, by] = iso([ESCENA.BUZ[0], ESCENA.BUZ[1], 22], ESCENA.P);
    this.ondas.innerHTML = [0, 1, 2].map((i) => `<path class="onda" data-i="${i}" d="M${bx - 10 - i * 7} ${by - 4 - i * 5} Q${bx} ${by - 16 - i * 9} ${bx + 10 + i * 7} ${by - 4 - i * 5}"/>`).join("");
    const [ax, ay] = ESCENA.ANTENNA;
    this.wifi.innerHTML = [0, 1, 2].map((i) => `<path class="onda-wifi" data-i="${i}" d="M${ax - 6 - i * 6} ${ay - 6 - i * 5} Q${ax} ${ay - 14 - i * 9} ${ax + 6 + i * 6} ${ay - 6 - i * 5}"/>`).join("");
  },
  dibujar() {
    const P = ESCENA.P;
    const ahora = performance.now();
    // balanceo de la cabeza según la última muestra física
    const objY = Math.max(-6, Math.min(6, HW.ay * 70 + HW.ax * 40));
    const objZ = Math.max(-6, Math.min(6, (HW.az - 1) * 60));
    this.cab.y += (objY - this.cab.y) * 0.35; this.cab.z += (objZ - this.cab.z) * 0.35;
    this.cabeza.setAttribute("transform", translateAlong(P, [0, this.cab.y, this.cab.z]));
    // mazo del collar: se recalcula con la cabeza
    const r = ESCENA.HARNESS_ROUTE.map((p) => [...p]);
    const g = [ESCENA.GLAND[0], ESCENA.GLAND[1] + this.cab.y, ESCENA.GLAND[2] + this.cab.z];
    const caida = [g[0], g[1], g[2] - 10];
    const pts = [...r, [g[0], g[1] * 0.5, 7 + (g[2] - 7) * 0.25], caida, g].map((p) => iso(p, P));
    const d = pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join("");
    this.mazo.forEach((m) => m.setAttribute("d", d));
    const i2c = ahora - HW.i2cFlash < 140 && MOTOR.modo !== "pausa";
    UI.svg.querySelector('[data-cable="mpu"]').classList.toggle("activo", i2c);
    for (const id of ["21", "22"]) UI.svg.querySelector(`[data-cable="${id}"]`).classList.toggle("activo", i2c);
    const hx = ahora - HW.hxFlash < 140 && MOTOR.modo !== "pausa";
    for (const id of ["4", "5"]) UI.svg.querySelector(`[data-cable="${id}"]`).classList.toggle("activo", hx);
    // LEDs
    for (const [n, el] of Object.entries(this.leds)) el.classList.toggle("on", !!HW.led[n]);
    UI.svg.querySelector('[data-cable="25"]').classList.toggle("activo", !!HW.led.verde);
    UI.svg.querySelector('[data-cable="26"]').classList.toggle("activo", !!HW.led.amarillo);
    UI.svg.querySelector('[data-cable="27"]').classList.toggle("activo", !!HW.led.rojo);
    // buzzer
    this.ondas.classList.toggle("on", HW.pwm > 0);
    UI.svg.querySelector('[data-cable="14"]').classList.toggle("activo", HW.pwm > 0);
    UI.svg.querySelector('[data-cable="13"]').classList.toggle("activo", HW.botonAbajo);
    // wifi
    this.wifi.classList.toggle("on", FW.mqtt.conectado && HW.wifi);
    // balanza: el plato baja un poco con el peso; la leche sube
    const hundir = -HW.kg * 0.12;
    this.plato.setAttribute("transform", translateAlong(P, [0, 0, hundir]));
    const Bk = ESCENA.BUCKET;
    const nivel = Bk.z + 2 + Math.min(1, HW.kg / 15) * Bk.h * 0.84;
    const rN = Bk.r + (Bk.rTop - Bk.r) * ((nivel - Bk.z) / Bk.h) - 0.8;
    if (HW.kg > 0.01) {
      const t = HW.t / 1000;
      const ola = HW.oleaje * 10;
      const anillo = [];
      for (let i = 0; i < 48; i++) {
        const a = (i / 48) * Math.PI * 2;
        const dz = ola * Math.sin(a * 2 + t * 9) * 0.5;
        anillo.push(iso([Bk.cx + Math.cos(a) * rN, Bk.cy + Math.sin(a) * rN, nivel + dz], P));
      }
      const borde = [];
      for (let i = 0; i < 72; i++) { const a = (i / 72) * Math.PI * 2; borde.push(iso([Bk.cx + Math.cos(a) * Bk.rTop, Bk.cy + Math.sin(a) * Bk.rTop, Bk.z + Bk.h], P)); }
      const pd = (ps) => ps.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join("") + "Z";
      let ondas = "";
      if (HW.vertiendo || HW.oleaje > 0.02) {
        for (let k = 0; k < 3; k++) {
          const fase = ((t * 1.4 + k / 3) % 1);
          const rr = 3 + fase * (rN - 6);
          const cx = Bk.cx - 8, cy = Bk.cy - 14;
          const ring = [];
          for (let i = 0; i < 32; i++) { const a = (i / 32) * Math.PI * 2; const px = cx + Math.cos(a) * rr, py = cy + Math.sin(a) * rr; if ((px - Bk.cx) ** 2 + (py - Bk.cy) ** 2 < (rN - 1) ** 2) ring.push(iso([px, py, nivel + 0.2], P)); else ring.push(null); }
          const segs = []; let cur = [];
          for (const p of ring) { if (p) cur.push(p); else { if (cur.length > 1) segs.push(cur); cur = []; } }
          if (cur.length > 1) segs.push(cur);
          ondas += `<path class="ola" style="opacity:${(1 - fase) * 0.8}" d="${segs.map((s) => s.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join("")).join("")}"/>`;
        }
      }
      this.leche.innerHTML = `<clipPath id="boca"><path d="${pd(borde)}"/></clipPath><g clip-path="url(#boca)"><path class="leche" d="${pd(anillo)}"/>${ondas}</g>`;
    } else this.leche.innerHTML = "";
    // chorro de leche desde la boquilla
    if (HW.vertiendo) {
      const a = iso(ESCENA.NOZZLE, P);
      const b = iso([ESCENA.NOZZLE[0], ESCENA.NOZZLE[1], nivel + hundir], P);
      const w = Math.sin(HW.t / 90) * 0.8;
      this.chorro.setAttribute("d", `M${a[0] - 1.6} ${a[1]} L${a[0] + 1.6} ${a[1]} L${b[0] + 2.4 + w} ${b[1]} L${b[0] - 2.4 + w} ${b[1]} Z`);
    } else this.chorro.setAttribute("d", "");
    // lecturas del encabezado
    document.body.classList.toggle("bloqueada", !!FW.bloqueado);
    $("#ind-wifi").dataset.on = HW.wifi ? "1" : "0";
  },
};

// Vistas con zoom (anima el viewBox del SVG)
const VISTA = {
  actual: ESCENA.VISTAS.completa.slice(), anim: 0,
  ir(nombre) {
    const destino = ESCENA.VISTAS[nombre]; if (!destino) return;
    $$("[data-vista]").forEach((b) => b.classList.toggle("activa", b.dataset.vista === nombre));
    document.body.dataset.vista = nombre;
    const desde = this.actual.slice(), t0 = performance.now(), dur = 700;
    cancelAnimationFrame(this.anim);
    const paso = (now) => {
      const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3);
      this.actual = desde.map((v, i) => v + (destino[i] - v) * e);
      UI.svg.setAttribute("viewBox", this.actual.map((v) => v.toFixed(1)).join(" "));
      if (p < 1) this.anim = requestAnimationFrame(paso);
    };
    this.anim = requestAnimationFrame(paso);
  },
};

// Zoom del HX711: 25 pulsos de SCK y los 24 bits de DT
const HXZ = {
  dibujar(u) {
    const el = $("#hxz");
    if (!el || el.closest("[hidden]")) return;
    if (this.ultimo && performance.now() - this.ultimo < 400 && MOTOR.modo === "continuo") return;
    this.ultimo = performance.now();
    const W = 760, H = 150, x0 = 64, paso = (W - x0 - 20) / 25.5;
    let sck = `M${x0 - 20} 52`, dt = "";
    const bits = [];
    for (let i = 0; i < 24; i++) bits.push((u.bits >> (23 - i)) & 1);
    let y = 112;
    let dtp = `M${x0 - 40} 112 L${x0 - 30} 112 L${x0 - 30} 128 `;
    for (let i = 0; i < 25; i++) {
      const xa = x0 + i * paso, xb = xa + paso * 0.5;
      sck += `L${xa} 52 L${xa} 22 L${xb} 22 L${xb} 52 `;
      if (i < 24) {
        const by = bits[i] ? 100 : 128;
        dtp += `L${xa - paso * 0.15} ${y === 112 ? 128 : y} L${xa - paso * 0.15} ${by} L${xa + paso * 0.85} ${by} `;
        y = by;
        dt += `<text x="${xa + paso * 0.25}" y="146" class="bit${bits[i] ? " uno" : ""}">${bits[i]}</text>`;
      }
    }
    sck += `L${W - 10} 52`;
    dtp += `L${W - 10} 128`;
    const hex = "0x" + u.bits.toString(16).toUpperCase().padStart(6, "0");
    el.innerHTML = `<svg viewBox="0 0 ${W} 160"><text x="4" y="40" class="et">SCK</text><text x="4" y="118" class="et">DT</text>
      <path class="sck" d="${sck}"/><path class="dtp" d="${dtp}"/>${dt}
      <text x="${x0 + 24 * paso + 2}" y="16" class="p25">25</text></svg>
      <div class="hx-dec"><span>24 bits = <code>${hex}</code></span><span>bit 23 = <b>${(u.bits >> 23) & 1}</b> → ${(u.bits & 0x800000) ? `negativo: ${hex} − 0x1000000 = <b>${u.valor}</b>` : `positivo: <b>${u.valor}</b>`}</span>
      <span>kg = (${u.valor} − ${Math.round(FW.balanza.offset)}) / ${pyFloat(FW.balanza.factor)} = <b>${((u.valor - FW.balanza.offset) / FW.balanza.factor).toFixed(3)}</b></span></div>`;
  },
};

// ======================================================================
// 8. Bucle de animación y controles
// ======================================================================
let ultimoCuadro = 0;
function cuadro(now) {
  const dt = ultimoCuadro ? Math.min(100, now - ultimoCuadro) : 16;
  ultimoCuadro = now;
  if (MOTOR.modo === "continuo") {
    MOTOR.correrHasta(HW.t + dt * MOTOR.velocidad);
    if (!FW.bloqueado) UI.bloqueo(false);
  }
  ESC.dibujar(); VAR.dibujar();
  requestAnimationFrame(cuadro);
}

const CONTROL = {
  init() {
    $("#btn-pausa").addEventListener("click", () => { RECORRIDO.salir(); MOTOR.modo === "continuo" ? MOTOR.parar() : MOTOR.continuo(); });
    $$("[data-vel]").forEach((b) => b.addEventListener("click", () => { RECORRIDO.salir(); MOTOR.velocidad = Number(b.dataset.vel); MOTOR.continuo(); UI.estadoMotor(); }));
    $("#btn-paso").addEventListener("click", () => { RECORRIDO.salir(); MOTOR.lento("vuelta", 260); UI.estadoMotor(); });
    $("#btn-saltar").addEventListener("click", () => saltarCalibracion());
    $("#btn-reiniciar").addEventListener("click", () => { RECORRIDO.salir(); MOTOR.reiniciar(); MOTOR.continuo(); });
    const mov = $("#ctl-mov");
    const setMov = () => { HW.amp = Math.pow(Number(mov.value) / 1000, 2); $("#ctl-mov-v").textContent = HW.amp.toFixed(3) + " g"; };
    mov.addEventListener("input", setMov); setMov();
    $$("[data-mov]").forEach((b) => b.addEventListener("click", () => { mov.value = String(Math.round(Math.sqrt(Number(b.dataset.mov)) * 1000)); setMov(); }));
    const kg = $("#ctl-kg");
    const setKg = () => { HW.kgObjetivo = Number(kg.value) / 10; $("#ctl-kg-v").textContent = HW.kgObjetivo.toFixed(1) + " kg"; };
    kg.addEventListener("input", setKg); setKg();
    $("#ctl-wifi").addEventListener("change", (e) => { HW.wifi = !e.target.checked; });
    $("#btn-pulsar").addEventListener("pointerdown", (e) => { e.preventDefault(); presionarBoton(); });
    $("#btn-pulsar").addEventListener("keydown", (e) => { if (e.key === " " || e.key === "Enter") { e.preventDefault(); presionarBoton(); setTimeout(() => soltarBoton(false), 200); } });
    // app
    $$("[data-cmd]").forEach((b) => b.addEventListener("click", () => {
      const t = { umbral: CFG.TOPICO_CFG_UMBRAL, muestreo: CFG.TOPICO_CFG_MUESTREO, tara: CFG.TOPICO_CMD_TARA, calibrar: CFG.TOPICO_CMD_CALIBRAR, buzzer: CFG.TOPICO_CMD_BUZZER }[b.dataset.cmd];
      const v = b.dataset.valor ?? $(`#v-${b.dataset.cmd}`).value;
      RED.desdeApp(t, v);
    }));
    $$("[data-vista]").forEach((b) => b.addEventListener("click", () => VISTA.ir(b.dataset.vista)));
    $("#btn-hx").addEventListener("click", () => { const p = $("#panel-hx"); p.hidden = !p.hidden; if (!p.hidden && HW.hxUltimo) HXZ.dibujar(HW.hxUltimo); });
    $("#btn-tema").addEventListener("click", () => { const b = document.body; b.dataset.theme = b.dataset.theme === "light" ? "dark" : "light"; });
    document.addEventListener("keydown", (e) => {
      if (e.target.closest("input")) return;
      if (e.key === " ") { e.preventDefault(); $("#btn-pausa").click(); }
      if (e.key === "ArrowRight" && RECORRIDO.activo) $("#rec-sig").click();
      if (e.key === "ArrowLeft" && RECORRIDO.activo) $("#rec-ant").click();
      if (e.key.toLowerCase() === "p" && !RECORRIDO.activo) $("#btn-paso").click();
    });
  },
};
function saltarCalibracion() {
  const m = FW.monitor;
  if (!m.calibrando || FW.fase !== "bucle") return;
  // equivalente a haber completado las ventanas con la actividad actual
  const est = muestraActividadEstimada();
  m.suma_calibracion = est * CFG.VENTANAS_CALIBRACION; m.ventanas_calibradas = CFG.VENTANAS_CALIBRACION;
  m.linea_base = Math.max(est, CFG.LINEA_BASE_MINIMA); m.calibrando = false;
  m.suma = 0; m.muestras = 0; m.inicio_ventana = ticks();
  UI.serial("— simulación: calibración saltada, linea_base = " + m.linea_base.toFixed(4) + " g (no es un print del firmware)", "sim");
}
function muestraActividadEstimada() {
  let s = 0; const t0 = HW.t;
  for (let i = 0; i < 100; i++) { HW.t = t0 + i * 100; const [a, b, c] = muestraMPU().map((v) => v / 16384); s += Math.abs(Math.sqrt(a * a + b * b + c * c) - 1); }
  HW.t = t0; return s / 100;
}

// ======================================================================
// 9. Recorridos guiados
// ======================================================================
const ESPERA_REAL = (ms) => new Promise((r) => setTimeout(r, ms));
const RECORRIDO = {
  activo: null, paso: 0, token: 0,
  lista: [
    {
      titulo: "1 · Arranque",
      pasos: [
        { txt: "Al encender, main.py crea los objetos: semáforo, buzzer, botón, el bus I2C con el MPU6050, el monitor de actividad y la balanza.", run: async (R) => { await R.reiniciar(); R.set({ amp: 0.02, kg: 0, wifi: true }); await R.lentoHasta(() => MOTOR.pila.some((e) => e.def === "def tara"), 360); } },
        { txt: "balanza.tara(): con el balde vacío, _promedio_crudo() promedia 5 lecturas crudas del HX711. Ese promedio queda como offset (el cero de la balanza).", run: async (R) => { await R.lentoHasta(() => LINEAS[M][R.lineaActual() - 1]?.includes("Balanza: tara lista"), 150); } },
        { txt: "mqtt.conectar(): primero el WiFi (wlan.connect y espera a que asocie). En Wokwi la red es «Wokwi-GUEST».", run: async (R) => { await R.lentoHasta(() => MOTOR.pila.some((e) => e.def === "def _conectar_wifi"), 240); await R.lentoHasta(() => !MOTOR.pila.some((e) => e.def === "def _conectar_wifi"), 120); } },
        { txt: "cliente.connect() abre la sesión en broker.hivemq.com y deja registrado el Last Will. Luego se suscribe a los 5 tópicos de comandos y publica «conectado» (retain).", run: async (R) => { await R.lentoHasta(() => LINEAS[M][R.lineaActual() - 1]?.includes("semaforo.mostrar(config.ESTADO_NORMAL)"), 330); } },
        { txt: "LED verde encendido y empieza la calibración: 3 ventanas de 10 s para aprender cuánto se mueve normalmente esta vaca.", run: async (R) => { await R.lentoHasta(() => FW.fase === "bucle" && MOTOR.vuelta.length > 2, 420); } },
        { txt: "Ya en el bucle: cada vuelta revisa las 7 tareas y duerme 5 ms. Las tareas a las que no les toca se saltan (mira las insignias «se salta: faltan … ms»). A ×20 se ven las 3 ventanas de calibración.", run: async (R) => { R.continuo(20); await R.esperarSim(() => !FW.monitor.calibrando); R.pausa(); } },
        { txt: "Calibración terminada: en la 3.ª ventana _calibrar() fija linea_base = promedio de las 3 (mínimo 0.02 g). Ojo: como calibrando ya quedó en False, main.py imprime y publica esa ventana como «[Vaca] … Razón: 0.00» (la razón aún no se calculó). Desde la siguiente ventana se compara actividad / línea base.", run: async (R) => { R.continuo(5); await R.esperarSim(() => FW.monitor.razon > 0, 30000); R.pausa(); } },
      ],
    },
    {
      titulo: "2 · Posible celo",
      pasos: [
        { txt: "La vaca está tranquila (0.03 g de movimiento). La línea base ya está calibrada.", run: async (R) => { await R.preparado({ amp: 0.03 }); R.continuo(5); await R.esperarReal(1500); R.pausa(); } },
        { txt: "La vaca se mueve mucho más (montas, inquietud): 0.10 g extra. Cada 100 ms la Tarea 1 lee el MPU6050 y suma |magnitud − 1 g|.", run: async (R) => { R.set({ amp: 0.1 }); RECORRIDO.marca = ticks(); R.continuo(1); await R.esperarReal(900); await R.vueltaLenta(() => diff(ticks(), FW.ultima_lectura_mpu) >= CFG.INTERVALO_LECTURA_MPU_MS, 380); } },
        { txt: "Las muestras se acumulan en monitor.suma y monitor.muestras. Se deja correr (×5) una ventana completa de 10 s con la vaca agitada.", run: async (R) => { R.continuo(5); await R.esperarSim(() => FW.monitor.inicio_ventana >= (RECORRIDO.marca || 0) && CFG.VENTANA_ACTIVIDAD_MS - (ticks() - FW.monitor.inicio_ventana) < 300, 40000); R.pausa(); } },
        { txt: "Se cierra la ventana: actividad = suma / muestras, razón = actividad / línea base. Si la razón ≥ 2.0 → CELO_PROBABLE.", run: async (R) => { await R.vueltaLenta(() => diff(ticks(), FW.monitor.inicio_ventana) >= CFG.VENTANA_ACTIVIDAD_MS, 430); } },
        { txt: "Resultado: LED rojo, buzzer intermitente (300 ms encendido / 300 ms apagado, Tarea 7) y dos publicaciones MQTT: actividad y estado. La línea base NO se ajusta durante el celo.", run: async (R) => { R.continuo(1); await R.esperarReal(4000); R.pausa(); } },
      ],
    },
    {
      titulo: "3 · Comando desde la app",
      pasos: [
        { txt: "El buzzer está sonando por un posible celo. Desde la app se publica «silenciar» en …/sistema/esp32/cmd/buzzer.", run: async (R) => { await R.preparado({ amp: 0.1, celo: true }); R.continuo(1); await R.esperarReal(1200); RED.desdeApp(CFG.TOPICO_CMD_BUZZER, "silenciar"); await R.esperarSim(() => RED.buzon.length > 0, 10000); R.pausa(); } },
        { txt: "El broker lo entrega al socket de la ESP32. En la Tarea 6, mqtt.revisar() llama a check_msg(); umqtt llama al callback _mensaje_recibido, que convierte bytes a texto y llama a procesar_comando.", run: async (R) => { await R.vueltaLenta(() => RED.buzon.length > 0, 420, () => LINEAS[M][R.lineaActual() - 1]?.includes("buzzer.silenciar(True)")); } },
        { txt: "buzzer.silenciar(True): silenciado = True y apaga el tono. La alarma sigue «activa» (el estado sigue siendo CELO_PROBABLE) pero ya no suena.", run: async (R) => { await R.lentoHasta(() => false, 420, null, "fin"); R.continuo(1); await R.esperarReal(2500); R.pausa(); } },
      ],
    },
    {
      titulo: "4 · Ordeño",
      pasos: [
        { txt: "El balde está vacío sobre la celda de carga. Se empieza a verter leche: la superficie se agita y el peso fluctúa.", run: async (R) => { await R.preparado({ amp: 0.03, kg: 0 }); R.set({ kg: 8 }); R.continuo(1); await R.esperarReal(2500); R.pausa(); } },
        { txt: "Tarea 2: cuando DT baja a 0 (dato listo, 10 veces por segundo), leer_crudo() saca 24 bits con 24 pulsos de SCK + el pulso 25. Abre «Zoom HX711» para verlo.", run: async (R) => { $("#panel-hx").hidden = false; await R.vueltaLenta(() => HW.hxListo, 300); } },
        { txt: "Mientras se vierte, las 5 últimas lecturas varían más de 20 g → «moviéndose». Si se presiona el botón ahora, el registro se rechaza.", run: async (R) => { R.continuo(1); await R.esperarSim(() => HW.vertiendo === false, 15000); await R.esperarReal(400); presionarBoton(); await R.vueltaLenta(() => FW.boton.ultima_lectura === 0 && diff(ticks(), FW.boton.tiempo_cambio) >= CFG.ANTIRREBOTE_MS, 330); soltarBoton(true); } },
        { txt: "Se espera a que la leche se calme: 5 lecturas seguidas dentro de 20 g → es_estable() = True.", run: async (R) => { R.continuo(1); await R.esperarSim(() => esEstable(), 20000); await R.esperarReal(1200); R.pausa(); } },
        { txt: "Ahora sí: se presiona el pulsador. Tras 50 ms sin rebotes, fue_presionado() devuelve True; el ordeño se registra y se publica.", run: async (R) => { presionarBoton(); await R.vueltaLenta(() => FW.boton.ultima_lectura === 0 && diff(ticks(), FW.boton.tiempo_cambio) >= CFG.ANTIRREBOTE_MS, 380); soltarBoton(true); } },
      ],
    },
    {
      titulo: "5 · Se cae la red",
      pasos: [
        { txt: "Todo conectado. Se corta el WiFi del router.", run: async (R) => { await R.preparado({ amp: 0.03 }); R.continuo(1); await R.esperarReal(1200); R.set({ wifi: false }); await R.esperarReal(300); R.pausa(); } },
        { txt: "En la siguiente operación de red falla el socket: «MQTT: conexión perdida» y mqtt.conectado = False. Los LEDs, el buzzer y la balanza siguen trabajando local.", run: async (R) => { await R.vueltaLenta(() => !FW.mqtt.conectado || MOTOR.tareas[6], 300, () => !FW.mqtt.conectado); } },
        { txt: "Reintento: revisar() llama a conectar() porque pasaron más de 15 s desde el último intento. _conectar_wifi() espera hasta 10 s al router (el bucle queda bloqueado mientras tanto).", run: async (R) => { R.continuo(5); await R.esperarSim(() => !!FW.bloqueado, 30000); R.continuo(3); await R.esperarSim(() => !FW.bloqueado, 15000); R.pausa(); } },
        { txt: "El broker deja de oír a la ESP32. Pasados 1.5 × keepalive = 90 s publica el Last Will: «desconectado» (retain) en …/sistema/esp32/conexion.", run: async (R) => { R.continuo(20); await R.esperarSim(() => RED.retenido[CFG.TOPICO_CONEXION] === "desconectado", 200000); R.continuo(1); await R.esperarReal(2500); R.pausa(); } },
        { txt: "Vuelve el WiFi. En el siguiente reintento (cada 15 s) la ESP32 se reconecta, se vuelve a suscribir y publica «conectado».", run: async (R) => { R.set({ wifi: true }); R.continuo(5); await R.esperarSim(() => FW.mqtt.conectado, 40000); R.continuo(1); await R.esperarReal(2500); R.pausa(); } },
      ],
    },
  ],
  init() {
    $("#escenarios").innerHTML = this.lista.map((r, i) => `<button data-rec="${i}">${r.titulo}</button>`).join("");
    $("#escenarios").addEventListener("click", (e) => { const b = e.target.closest("[data-rec]"); if (b) this.iniciar(Number(b.dataset.rec)); });
    $("#rec-sig").addEventListener("click", () => { if (this.ocupado) return; if (this.paso < this.activo.pasos.length - 1) this.irA(this.paso + 1); else this.salir(); });
    $("#rec-ant").addEventListener("click", () => { if (this.ocupado) return; if (this.paso > 0) this.repetirHasta(this.paso - 1); });
    $("#rec-x").addEventListener("click", () => this.salir());
  },
  iniciar(i) {
    VISTA.ir(["protoboard", "collar", "protoboard", "balanza", "completa"][i]);
    this.activo = this.lista[i]; this.indice = i; this.paso = -1;
    $$("#escenarios button").forEach((b) => b.classList.toggle("activa", Number(b.dataset.rec) === i));
    $("#recorrido").hidden = false;
    $("#rec-titulo").textContent = this.activo.titulo;
    this.irA(0);
  },
  async repetirHasta(n) {
    // volver atrás = repetir el escenario hasta ese paso
    const i = this.indice; this.iniciarSilencioso(i);
    for (let k = 0; k < n; k++) { this.paso = k; await this.ejecutar(k, true); }
    this.irA(n);
  },
  iniciarSilencioso(i) { this.activo = this.lista[i]; this.paso = -1; },
  async irA(n) {
    this.paso = n;
    $("#rec-n").textContent = `Paso ${n + 1} de ${this.activo.pasos.length}`;
    $("#rec-txt").textContent = this.activo.pasos[n].txt;
    $("#rec-puntos").innerHTML = this.activo.pasos.map((_, k) => `<i class="${k < n ? "hecho" : k === n ? "ahora" : ""}"></i>`).join("");
    await this.ejecutar(n);
  },
  async ejecutar(n, rapido) {
    const tok = ++this.token;
    this.ocupado = true;
    $("#rec-sig").disabled = true;
    const R = this.api(tok, rapido);
    try { await this.activo.pasos[n].run(R); } catch (e) { if (e !== "cancelado") console.error(e); }
    if (tok !== this.token) return;
    this.ocupado = false;
    $("#rec-sig").disabled = false;
    $("#rec-sig").textContent = n < this.activo.pasos.length - 1 ? "Siguiente ▶" : "Terminar ✓";
  },
  salir() {
    if (!this.activo) return;
    VISTA.ir("completa");
    this.token++; this.activo = null; this.ocupado = false;
    MOTOR.cond = null; MOTOR.alCumplir = null; MOTOR.alParar = null;
    if (MOTOR.modo === "lento") MOTOR.parar();
    $("#recorrido").hidden = true;
    $$("#escenarios button").forEach((b) => b.classList.remove("activa"));
  },
  api(tok, rapido) {
    const vivo = () => { if (tok !== this.token) throw "cancelado"; };
    const R = {
      lineaActual: () => { const v = MOTOR.vuelta; for (let i = v.length - 1; i >= 0; i--) if (v[i].tipo === "linea") return v[i].f === M ? v[i].l : -1; return -1; },
      set(o) {
        if (o.amp !== undefined) { HW.amp = o.amp; $("#ctl-mov").value = String(Math.round(Math.sqrt(o.amp) * 1000)); $("#ctl-mov-v").textContent = o.amp.toFixed(3) + " g"; }
        if (o.kg !== undefined) { HW.kgObjetivo = o.kg; $("#ctl-kg").value = String(o.kg * 10); $("#ctl-kg-v").textContent = o.kg.toFixed(1) + " kg"; }
        if (o.wifi !== undefined) { HW.wifi = o.wifi; $("#ctl-wifi").checked = !o.wifi; }
      },
      async reiniciar() { MOTOR.reiniciar(); MOTOR.modo = "pausa"; UI.estadoMotor(); },
      continuo(v) { vivo(); MOTOR.velocidad = v; MOTOR.continuo(); UI.estadoMotor(); },
      pausa() { vivo(); MOTOR.parar(); },
      esperarReal: async (ms) => { await ESPERA_REAL(rapido ? 0 : ms); vivo(); },
      async esperarSim(cond, maxMs = 120000) {
        const t0 = HW.t;
        if (rapido) { MOTOR.modo = "pausa"; while (!cond() && HW.t - t0 < maxMs) { MOTOR.correrHasta(HW.t + 50); } vivo(); return; }
        while (!cond() && HW.t - t0 < maxMs) { await ESPERA_REAL(30); vivo(); }
      },
      // estado listo para un escenario: arranca, calibra en silencio y conecta
      async preparado(o = {}) {
        MOTOR.reiniciar(); MOTOR.modo = "pausa";
        R.set({ amp: 0.03, kg: o.kg ?? 0, wifi: true });
        while (!(FW.fase === "bucle")) MOTOR.correrHasta(HW.t + 100);
        saltarCalibracion();
        if (o.celo) {
          R.set({ amp: o.amp });
          FW.monitor.inicio_ventana = ticks() - CFG.VENTANA_ACTIVIDAD_MS + 10500 - 10000;
          MOTOR.correrHasta(HW.t + CFG.VENTANA_ACTIVIDAD_MS + 200);
        } else R.set({ amp: o.amp ?? 0.03 });
        MOTOR.correrHasta(HW.t + 300);
        UI.estadoMotor(); vivo();
      },
      // ejecuta línea por línea hasta que la condición se cumpla al inicio de una línea
      lentoHasta(cond, cada = 420, inicio = null, unaVuelta = false) {
        vivo();
        return new Promise((ok, mal) => {
          if (rapido) { MOTOR.modo = "pausa"; let n = 0; while (!cond() && n++ < 200000) { const ev = MOTOR.siguiente(); MOTOR.procesar(ev); if (unaVuelta && ev.tipo === "vuelta" && n > 3) break; } ok(); return; }
          MOTOR.modo = "lento"; MOTOR.lentoCada = cada; UI.estadoMotor();
          clearTimeout(MOTOR.lentoTimer);
          let empezo = !inicio;
          let vueltas = 0;
          const tic = () => {
            if (tok !== RECORRIDO.token) { mal("cancelado"); return; }
            if (!empezo) { // correr rápido hasta la condición de inicio
              let n = 0; while (n++ < 5000) { const ev = MOTOR.siguiente(); MOTOR.procesar(ev); if (ev.tipo === "linea" && inicio()) { empezo = true; UI.lineaActual(ev); break; } }
              MOTOR.lentoTimer = setTimeout(tic, cada); return;
            }
            const ev = MOTOR.siguiente();
            if (ev.tipo === "vuelta" && unaVuelta && (unaVuelta === "fin" || ++vueltas > 1)) { MOTOR.pendiente = ev; MOTOR.modo = "pausa"; UI.estadoMotor(); ok(); return; }
            MOTOR.procesar(ev);
            let espera = 0;
            if (ev.tipo === "linea") { espera = esperaLinea(ev, 70, cada); if (espera > 5 || RAPIDOS.n % 9 === 0) UI.lineaActual(ev); }
            else if (ev.tipo === "tarea") UI.tareaVivo(ev);
            else if (ev.tipo === "evento") { UI.nota(ev.texto); espera = cada * 2; }
            else if (ev.tipo === "dormir") UI.refrescar();
            if (ev.tipo === "linea" && cond()) { MOTOR.modo = "pausa"; UI.estadoMotor(); ok(); return; }
            MOTOR.lentoTimer = setTimeout(tic, espera);
          };
          tic();
        });
      },
      // corre rápido hasta la vuelta en la que se cumple `cuando` y la muestra línea por línea
      async vueltaLenta(cuando, cada = 420, hasta = null) {
        vivo();
        // avanzar en continuo hasta el inicio de esa vuelta
        if (!rapido) { MOTOR.modo = "continuo"; MOTOR.velocidad = 1; }
        await new Promise((ok) => {
          MOTOR.cond = cuando; MOTOR.alCumplir = ok;
          if (rapido) { MOTOR.modo = "pausa"; let g = 0; while (MOTOR.cond && g++ < 4000) MOTOR.correrHasta(HW.t + 50); ok(); }
        });
        vivo();
        MOTOR.modo = "pausa";
        await R.lentoHasta(hasta || (() => false), cada, null, true);
      },
    };
    return R;
  },
};

// ======================================================================
// 10. Arranque
// ======================================================================
UI.init(); VAR.init(); ESC.init(); CONTROL.init(); RECORRIDO.init();
MOTOR.reiniciar();
MOTOR.velocidad = 1; MOTOR.continuo();
requestAnimationFrame(cuadro);
window.SIM = { MOTOR, FW, HW, RED, RECORRIDO, UI, lineaDe, erroresLinea };
