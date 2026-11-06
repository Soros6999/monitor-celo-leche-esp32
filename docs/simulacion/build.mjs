// build.mjs — Genera docs/simulacion/index.html (autocontenido, sin internet).
//   node docs/simulacion/build.mjs
// Lee el código REAL de firmware/*.py y config.py en cada compilación, así
// la página nunca se desfasa del firmware.
import { readFileSync, writeFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import * as k from "./kit/iso-kit.mjs";
import * as E from "./escena.mjs";

const AQUI = dirname(fileURLToPath(import.meta.url));
const FIRMWARE = join(AQUI, "..", "..", "firmware");

// ---------- Fuentes y configuración ----------
const ARCHIVOS = ["main.py", "actividad.py", "balanza.py", "hx711.py", "indicadores.py", "boton.py", "mpu6050.py", "comunicacion.py", "config.py"];
const FUENTES = Object.fromEntries(ARCHIVOS.map((f) => [f, readFileSync(join(FIRMWARE, f), "utf8").replace(/\r\n/g, "\n").replace(/\n$/, "")]));

function leerConfig(texto) {
  const cfg = {};
  for (const linea of texto.split("\n")) {
    const m = linea.match(/^([A-Z][A-Z0-9_]*)\s*=\s*(.+?)\s*(#.*)?$/);
    if (!m) continue;
    const expr = m[2].trim();
    const partes = expr.split("+").map((p) => p.trim());
    const valor = partes.map((p) => {
      if (/^".*"$/.test(p)) return p.slice(1, -1);
      if (/^-?\d+(\.\d+)?$/.test(p)) return Number(p);
      if (p in cfg) return cfg[p];
      throw new Error(`config.py: no entiendo «${p}» en ${m[1]}`);
    });
    cfg[m[1]] = valor.length === 1 ? valor[0] : valor.join("");
  }
  return cfg;
}
const CFG = leerConfig(FUENTES["config.py"]);
for (const clave of ["INTERVALO_LECTURA_MPU_MS", "VENTANA_ACTIVIDAD_MS", "VENTANAS_CALIBRACION", "ALFA_LINEA_BASE", "LINEA_BASE_MINIMA", "UMBRAL_ACTIVIDAD_ALTA", "UMBRAL_CELO", "DENSIDAD_LECHE", "FACTOR_CALIBRACION", "MUESTRAS_ESTABILIDAD", "TOLERANCIA_ESTABLE_KG", "ANTIRREBOTE_MS", "MQTT_REINTENTO_MS", "MQTT_KEEPALIVE_S", "MQTT_PING_MS", "WIFI_TIMEOUT_MS", "INTERVALO_PUBLICACION_MS", "BUZZER_INTERVALO_MS", "TOPICO_CMD_BUZZER", "PREFIJO"]) {
  if (!(clave in CFG)) throw new Error("Falta " + clave + " en config.py");
}

// ---------- Escena ----------
const theme = process.argv.includes("--dark") ? "dark" : "light";
const svg = E.build();
const ESCENA = { VISTAS: E.VISTAS, P: E.P, CABLES: E.CABLES.map(({ id, info }) => ({ id, info })), HARNESS_ROUTE: E.HARNESS_ROUTE, GLAND: E.GLAND, BUCKET: E.BUCKET, NOZZLE: E.NOZZLE, BUZ: E.BUZ, ANTENNA: E.ANTENNA };

const kitFuente = readFileSync(join(AQUI, "kit", "iso-kit.mjs"), "utf8").replace(/^export /gm, "").replace(/<\/script/gi, "<\\/script");
const simFuente = readFileSync(join(AQUI, "sim.js"), "utf8");
const css = readFileSync(join(AQUI, "estilos.css"), "utf8");

const T = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");
const cfgCorto = (t) => t.replace(CFG.PREFIJO + "/", "");

const html = `<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Simulación · Monitor de celo y leche (ESP32)</title>
<style>${k.ISO_CSS}${css}</style></head>
<body class="iso" data-theme="${theme}" data-modo="continuo">
<header class="barra">
  <div class="marca"><b>Monitor de celo y leche</b><span>ESP32 · MicroPython · así corre <code>main.py</code></span></div>
  <div class="grupo"><span class="rot">Recorridos</span><nav id="escenarios"></nav></div>
  <div class="grupo tiempo">
    <button id="btn-pausa" class="fuerte">⏸ Pausa</button>
    <button data-vel="1">×1</button><button data-vel="5">×5</button><button data-vel="20">×20</button>
    <button id="btn-paso" title="Ejecuta una vuelta del bucle, línea por línea (tecla P)">Paso ⏭</button>
    <button id="btn-saltar" title="Termina la calibración con la actividad actual">Saltar calibración</button>
    <button id="btn-reiniciar" title="Reiniciar la ESP32">↺ Reiniciar</button>
    <button id="btn-tema" title="Tema claro / oscuro">◐</button>
  </div>
</header>
<div id="errores" hidden></div>
<main class="grid">
  <section class="izq">
    <div id="recorrido" hidden>
      <div class="rec-cab"><b id="rec-titulo"></b><span id="rec-n"></span><span id="rec-puntos"></span><button id="rec-x" title="Salir del recorrido">✕</button></div>
      <p id="rec-txt"></p>
      <div class="rec-pie"><button id="rec-ant">◀ Anterior</button><button id="rec-sig" class="fuerte">Siguiente ▶</button></div>
    </div>
    <div class="tarjeta escena">
      <div class="esquina sup-izq">Fig 1 · Banco de pruebas</div>
      <div class="vistas"><span class="rot">Vista</span><button data-vista="completa" class="activa">completa</button><button data-vista="protoboard">protoboard</button><button data-vista="collar">collar</button><button data-vista="balanza">balanza</button></div>
      <div class="lecturas">
        <span class="chip" id="lectura-estado" data-e="cal">—</span>
        <span class="dato"><i>razón</i><b id="lectura-razon">—</b></span>
        <span class="dato"><i>balde</i><b id="lectura-litros">0.00 L</b></span>
        <span class="dato"><i>reloj ESP32</i><b id="lectura-reloj">0.0 s</b></span>
        <span class="ventana"><i>ventana</i><span class="barra-v"><span id="barra-ventana"></span></span><em id="ventana-txt"></em></span>
      </div>
      ${svg}
      <div class="aviso">En la realidad el <b>collar</b> y la <b>balanza</b> serían dos dispositivos distintos; en este prototipo comparten una ESP32.</div>
      <div class="pista">Pasa el cursor por un cable para ver su pin · Haz clic en el botón azul para presionarlo</div>
      <div class="bloqueo-aviso">⏳ Bucle detenido: <code>_conectar_wifi()</code> espera al router (hasta ${CFG.WIFI_TIMEOUT_MS / 1000} s)</div>
      <div id="tooltip" hidden></div>
    </div>
    <div class="controles">
      <div class="ctl">
        <label for="ctl-mov">Movimiento de la vaca <b id="ctl-mov-v"></b></label>
        <input id="ctl-mov" type="range" min="0" max="1000" value="173">
        <div class="presets"><button data-mov="0.0">quieta</button><button data-mov="0.03">rumiando</button><button data-mov="0.065">caminando</button><button data-mov="0.1">celo</button><button data-mov="1">1 g</button></div>
      </div>
      <div class="ctl">
        <label for="ctl-kg">Leche en el balde <b id="ctl-kg-v"></b></label>
        <input id="ctl-kg" type="range" min="0" max="150" value="0">
        <div class="presets"><span>0 a 15 kg · se vierte a 1.2 kg/s</span></div>
      </div>
      <div class="ctl botones">
        <button id="btn-pulsar" class="pulsador">● Pulsador (GPIO 13)</button>
        <label class="interruptor"><input type="checkbox" id="ctl-wifi"><span></span>Cortar WiFi <i id="ind-wifi" data-on="1"></i></label>
        <button id="btn-hx">Zoom HX711</button>
      </div>
    </div>
    <div id="panel-hx" class="tarjeta" hidden><div class="hx-tit">Última lectura del HX711 · <code>leer_crudo()</code>: 24 pulsos de SCK leen 24 bits de DT; el pulso 25 elige canal A, ganancia 128</div><div id="hxz"><p class="vacio">Esperando una lectura…</p></div></div>
    <div class="red tarjeta">
      <div class="nodos">
        <div class="nodo" id="red-esp" data-ok="0"><b>ESP32</b><span>WiFi «${T(CFG.WIFI_SSID)}» · cliente ${T(CFG.MQTT_CLIENTE_ID)}_…</span><span id="red-esp-estado"></span><span id="red-esp-ultimo"></span></div>
        <div class="nodo broker" id="red-broker" data-sesion="0"><b>Broker MQTT</b><span>${T(CFG.MQTT_BROKER)}:${CFG.MQTT_PUERTO}</span><span id="broker-estado"></span><span id="broker-retenido"></span><span id="broker-keep"></span></div>
        <div class="nodo app" id="red-app"><b>App de escritorio</b><div id="app-datos"></div></div>
      </div>
      <div id="paquetes"></div>
      <div class="red-pie">
        <span id="broker-log"></span>
        <div class="cmds">
          <span class="rot">Comandos de la app:</span>
          <span class="cmd"><input id="v-umbral" value="1.8" size="3"><button data-cmd="umbral" title="${T(cfgCorto(CFG.TOPICO_CFG_UMBRAL))}">umbral</button></span>
          <span class="cmd"><input id="v-muestreo" value="5000" size="4"><button data-cmd="muestreo" title="${T(cfgCorto(CFG.TOPICO_CFG_MUESTREO))}">muestreo</button></span>
          <button data-cmd="tara" data-valor="1" title="${T(cfgCorto(CFG.TOPICO_CMD_TARA))}">tara</button>
          <span class="cmd"><input id="v-calibrar" value="10" size="2"><button data-cmd="calibrar" title="${T(cfgCorto(CFG.TOPICO_CMD_CALIBRAR))}">calibrar</button></span>
          <button data-cmd="buzzer" data-valor="silenciar" title="${T(cfgCorto(CFG.TOPICO_CMD_BUZZER))}">silenciar</button>
          <button data-cmd="buzzer" data-valor="activar" title="${T(cfgCorto(CFG.TOPICO_CMD_BUZZER))}">activar</button>
        </div>
      </div>
    </div>
  </section>
  <section class="der">
    <div class="tarjeta codigo-tarjeta">
      <div id="tabs"></div>
      <div class="pila-nota"><span id="pila">main.py</span><span id="nota"></span></div>
      <div class="codigo-cuerpo"><ol id="tareas"></ol><div id="codigo"></div></div>
    </div>
    <div class="abajo">
      <div class="tarjeta"><h3>Variables <small>(nombres del código)</small></h3><div id="vars"></div></div>
      <div class="tarjeta"><h3>Monitor serial <small>(textos exactos de los print)</small></h3><div id="serial"></div></div>
    </div>
  </section>
</main>
<script>
const FUENTES = ${JSON.stringify(FUENTES).replace(/<\//g, "<\\/")};
const CFG = ${JSON.stringify(CFG)};
const ESCENA = ${JSON.stringify(ESCENA)};
${kitFuente}
${simFuente}
</script>
</body></html>`;

writeFileSync(join(AQUI, "index.html"), html);
console.log("escrito index.html", (html.length / 1024).toFixed(0) + " KB", "· tema", theme);
