// escena.mjs — Geometría isométrica del banco de pruebas.
// Se ejecuta en Node (build.mjs). Devuelve el SVG estático y los datos que
// necesita la página para mover las piezas (proyección, anclas, cables).
//
// Mundo: x e y sobre el banco, z hacia arriba, unidades ≈ 1 px.
// Izquierda (x < -120): estación de ordeño (celda de carga + balde).
// Centro: protoboard con la ESP32 DevKit, LEDs, buzzer, pulsador y HX711.
// Derecha (x > 120): la vaca con el collar (MPU6050).

import * as k from "./kit/iso-kit.mjs";

export const W = 1240;
export const H = 640;
const AZ = 70;

// ---------- Planos principales ----------
const BENCH = { x: -350, y: -112, w: 700, d: 224, r: 10 };
const BENCH_H = 12;
const FOOT_H = 6;
const STATION = { x: -334, y: -92, w: 200, d: 184, r: 6 };
const BB = { x: -112, y: -72, w: 224, d: 144, r: 4 };      // protoboard
const BB_H = 10;
const PLINTH = { x: 124, y: -92, w: 212, d: 184, r: 6 };    // base de la vaca

// ESP32 DevKit C v4 (USB hacia -x, antena hacia +x)
const PCB = { x: -72, y: -26, w: 116, d: 52, r: 2 };
const PCB_Z = 18;
const PCB_T = 2.4;
const PITCH = 5.6;
const pinX = (i) => 36 - i * PITCH;
// Columna frontal (+y) y trasera (-y) de la DevKit C v4, desde la antena hacia el USB
export const PINES_FRENTE = ["3V3", "EN", "VP", "VN", "34", "35", "32", "33", "25", "26", "27", "14", "12", "GND", "13", "D2", "D3", "CMD", "5V"];
export const PINES_ATRAS = ["GND", "23", "22", "TX", "RX", "21", "GND", "19", "18", "5", "17", "16", "4", "0", "2", "15", "D1", "D0", "CLK"];
const HOLE_Y = 30.5; // fila de agujeros justo fuera de los pines
const frente = (name) => pinX(PINES_FRENTE.indexOf(name));
const atras = (name) => pinX(PINES_ATRAS.indexOf(name));

// Estación de ordeño
const CELL = { x: -310, y: -11, w: 132, d: 22, r: 1.5 };
const CELL_Z = 22;
const CELL_H = 20;
const PLAT_C = [-238, 0];
const PLAT_R = 60;
const PLAT_Z = 56;
export const BUCKET = { cx: -238, cy: 0, r: 44, rTop: 48, z: PLAT_Z + 4, h: 74 };

// Vaca (mira hacia -x)
const COW = { body: { x: 196, y: -24, w: 104, d: 48, r: 16 }, bodyZ: 52, bodyH: 44 };
export const COLLAR_X = 186;
export const GLAND = [COLLAR_X, 0, 46];

const P = k.fitProjection(
  [
    ...k.boxCorners(BENCH, -BENCH_H - FOOT_H, 0),
    [-238, -66, 196],
    [140, 0, 124],
  ],
  W,
  H,
  { pad: 22, azimuth: AZ, elevation: 30 },
);
export { P };

const at = (p) => k.iso(p, P);
const S = (paths, style) => k.solidSvg(paths, style);
const L = (d, style) => k.lineSvg(d, style);
const D = (points, style) => k.dotsSvg(points, style);
const r1 = (v) => Math.round(v * 10) / 10;
const pathOf = (pts) => pts.map((p, i) => `${i ? "L" : "M"}${r1(p[0])} ${r1(p[1])}`).join("");
const byDepth = (pts) => [...pts].sort((a, b) => k.depthOf([a[0], a[1], 0], P) - k.depthOf([b[0], b[1], 0], P));
const halo = (plan, z, h, blur) => `<path class="iso-halo" d="${k.haloOf(plan, z, h, P)}"${blur ? ` style="filter:blur(${blur}px)"` : ""}/>`;

// Polígono sobre una cara: plano y = const (cara frontal) o z = const (cara superior)
const onFaceY = (pts, y) => pathOf(pts.map(([x, z]) => at([x, y, z]))) + "Z";
const onFaceX = (pts, x) => pathOf(pts.map(([y, z]) => at([x, y, z]))) + "Z";
const onTopZ = (pts, z) => pathOf(pts.map(([x, y]) => at([x, y, z]))) + "Z";
const blob = (cx, cy, rx, ry, seed, n = 14) => {
  const out = [];
  for (let i = 0; i < n; i++) {
    const a = (i / n) * Math.PI * 2;
    const w = 1 + 0.18 * Math.sin(a * 3 + seed) + 0.1 * Math.cos(a * 5 + seed * 2);
    out.push([cx + Math.cos(a) * rx * w, cy + Math.sin(a) * ry * w]);
  }
  return out;
};

// ---------- Banco ----------
function bench() {
  const out = [halo(BENCH, -BENCH_H - FOOT_H, BENCH_H + FOOT_H)];
  for (const [x, y] of byDepth(k.corners(BENCH, 26))) {
    out.push(S(k.cylinder(x, y, 9, -BENCH_H - FOOT_H, 2, P, 28), { tone: "lo" }));
    out.push(S(k.cylinder(x, y, 7, -BENCH_H - FOOT_H + 2, FOOT_H - 2, P, 28), { tone: "mid" }));
  }
  out.push(S(k.slabOf(BENCH, -BENCH_H, BENCH_H, P, 8, 1.6), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(BENCH, 6), 0, P), { tone: "faint" }));
  const screws = k.corners(BENCH, 12);
  out.push(L(screws.map(([x, y]) => k.ring(x, y, 2.6, 0, P, 16)).join(""), { tone: "lo" }));
  out.push(D(screws.map(([x, y]) => at([x, y, 0])), { size: 0.7 }));
  // regla frontal
  const strip = { x: -300, y: BENCH.y + BENCH.d - 14, w: 600, d: 8, r: 1 };
  out.push(S(k.slabOf(strip, 0, 0.6, P, 3), { tone: "lo", crease: "none" }));
  const t = k.topTicks(strip.x + 4, strip.x + strip.w - 4, 5, 5, strip.y + 0.8, 0.6, [2.2, 4.2], P);
  out.push(L(t.minor, { tone: "lo" }), L(t.major, { tone: "mid" }));
  out.push(D([at([strip.x + 2, strip.y + 4, 0.6]), at([strip.x + strip.w - 2, strip.y + 4, 0.6])], { size: 0.55 }));
  return out.join("");
}

// ---------- Estación de ordeño ----------
function stationBase() {
  const out = [halo(STATION, 0, 8, 6)];
  out.push(S(k.slabOf(STATION, 0, 8, P, 6, 1), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(STATION, 5), 8, P), { tone: "faint" }));
  const sc = k.corners(STATION, 9);
  out.push(L(sc.map(([x, y]) => k.ring(x, y, 2.2, 8, P, 14)).join(""), { tone: "lo" }));
  out.push(D(sc.map(([x, y]) => at([x, y, 8])), { size: 0.6 }));
  // placa de identificación
  const plate = { x: -322, y: 52, w: 46, d: 26, r: 1.5 };
  out.push(S(k.slabOf(plate, 8, 0.8, P, 3), { tone: "lo", crease: "none" }));
  out.push(L(k.planOutline(k.insetPlan(plate, 2), 8.8, P, 3), { tone: "faint" }));
  out.push(k.faceTextSvg(k.topMatrix([plate.x + 5, plate.y + 10], 8.8, P, "x"), "BALANZA", { size: 5.2, tone: "mid" }));
  [16, 21].forEach((y, i) => out.push(L(k.lineOnTop([plate.x + 5, plate.y + y], [plate.x + (i ? 26 : 36), plate.y + y], 8.8, P), { tone: "lo", free: true })));
  return out.join("");
}

function loadCell() {
  const out = [];
  // bloque fijo (izquierda) atornillado a la base
  const fixed = { x: -316, y: -15, w: 36, d: 30, r: 1.5 };
  out.push(S(k.slabOf(fixed, 8, CELL_Z - 8, P, 3, 0.6), { tone: "mid" }));
  out.push(D([at([-306, 8, 8.1]), at([-290, 8, 8.1])].map((p) => p), { size: 0.4 }));
  // barra de aluminio
  out.push(S(k.slabOf(CELL, CELL_Z, CELL_H, P, 3, 0.8), { tone: "hi", crease: "lo" }));
  // agujero binocular en la cara frontal (+y)
  const fy = CELL.y + CELL.d;
  const hz = CELL_Z + CELL_H / 2;
  const cx0 = -253, cx1 = -235, hr = 6.2;
  out.push(L(k.sideRing([cx0, fy, hz], hr, "y", P, 28) + k.sideRing([cx1, fy, hz], hr, "y", P, 28), { tone: "mid" }));
  out.push(L(k.segment([cx0, fy, hz + hr], [cx1, fy, hz + hr], P) + k.segment([cx0, fy, hz - hr], [cx1, fy, hz - hr], P), { tone: "mid" }));
  out.push(`<path class="hueco" d="${onFaceY([...Array(13)].map((_, i) => { const a = Math.PI / 2 + (i / 12) * Math.PI; return [cx0 + Math.cos(a) * hr, hz + Math.sin(a) * hr]; }).concat([...Array(13)].map((_, i) => { const a = -Math.PI / 2 + (i / 12) * Math.PI; return [cx1 + Math.cos(a) * hr, hz + Math.sin(a) * hr]; })), fy)}"/>`);
  // galgas extensiométricas (rectángulos sobre la cara superior)
  for (const x of [cx0 - 2, cx1 - 2]) {
    out.push(`<path class="galga" d="${onTopZ([[x, -6], [x + 6, -6], [x + 6, 6], [x, 6]], CELL_Z + CELL_H + 0.1)}"/>`);
  }
  out.push(D([at([-302, 0, CELL_Z + CELL_H]), at([-288, 0, CELL_Z + CELL_H])], { size: 0.65, tone: "hi" }));
  // flecha de carga grabada
  out.push(L(k.lineOnTop([-206, 0], [-194, 0], CELL_Z + CELL_H, P) + k.lineOnTop([-198, -3], [-194, 0], CELL_Z + CELL_H, P) + k.lineOnTop([-198, 3], [-194, 0], CELL_Z + CELL_H, P), { tone: "lo" }));
  return out.join("");
}

function platform() {
  // bloque móvil (derecha) y plato
  const out = [];
  const spacer = { x: -214, y: -15, w: 36, d: 30, r: 1.5 };
  out.push(S(k.slabOf(spacer, CELL_Z + CELL_H, PLAT_Z - CELL_Z - CELL_H, P, 3, 0.5), { tone: "mid" }));
  out.push(`<path class="iso-halo" d="${k.haloOf({ x: PLAT_C[0] - 50, y: -50, w: 100, d: 100, r: 50 }, PLAT_Z - 2, 0.1, P)}" style="filter:blur(5px);opacity:.5"/>`);
  out.push(S(k.cylinder(PLAT_C[0], PLAT_C[1], PLAT_R, PLAT_Z, 4, P, 72, 1), { tone: "mid" }));
  out.push(L(k.ring(PLAT_C[0], PLAT_C[1], PLAT_R - 5, PLAT_Z + 4, P, 72), { tone: "faint" }));
  const bolts = [0, 1, 2, 3].map((i) => [PLAT_C[0] + Math.cos(i * Math.PI / 2 + Math.PI / 4) * (PLAT_R - 9), Math.sin(i * Math.PI / 2 + Math.PI / 4) * (PLAT_R - 9)]);
  out.push(D(bolts.map(([x, y]) => at([x, y, PLAT_Z + 4])), { size: 0.7, tone: "mid" }));
  return out.join("");
}

// Balde: cuerpo + borde + asa. La leche se dibuja en vivo dentro de "milk".
function bucketBack() {
  const { cx, cy, r, rTop, z, h } = BUCKET;
  const out = [];
  const body = [];
  // Cuerpo troncocónico: muchos anillos con radio creciente
  const n = 64;
  const ring = (rad, zz) => [...Array(n)].map((_, i) => { const a = (i / n) * Math.PI * 2; return [cx + Math.cos(a) * rad, cy + Math.sin(a) * rad, zz]; });
  const bottom = ring(r, z), top = ring(rTop, z + h);
  // silueta = casco de ambos anillos proyectados
  const pts = [...bottom, ...top].map(at);
  const hull = convexHull(pts);
  out.push(`<path class="iso-fill" d="${pathOf(hull)}Z"/>`);
  // sombreado vertical suave: franjas por ángulo
  const view = Math.atan2(Math.sin(AZ * Math.PI / 180), Math.cos(AZ * Math.PI / 180));
  for (let i = 0; i < n; i++) {
    const a0 = (i / n) * Math.PI * 2, a1 = ((i + 1) / n) * Math.PI * 2;
    const facing = Math.cos((a0 + a1) / 2 - view);
    if (facing <= 0) continue;
    const light = Math.cos((a0 + a1) / 2 - (view + 0.9));
    const shade = light > 0.55 ? 3 : light > 0.1 ? 2 : light > -0.4 ? 1 : 0;
    body.push(`<path class="iso-shade" data-shade="${shade}" d="${pathOf([bottom[i], bottom[(i + 1) % n], top[(i + 1) % n], top[i]].map(at))}Z"/>`);
  }
  out.push(...body);
  // aros de refuerzo
  out.push(L(k.sideArc(cx, cy, r + 0.6, z + 6, P, 48), { tone: "lo" }));
  out.push(L(k.sideArc(cx, cy, r + (rTop - r) * 0.55 + 0.6, z + h * 0.55, P, 48), { tone: "faint" }));
  out.push(`<path class="iso-line iso-edge" data-tone="mid" d="${pathOf(hull)}Z"/>`);
  // boca: interior (pared trasera) visible
  out.push(`<path class="balde-interior" d="${k.ring(cx, cy, rTop, z + h, P, 72)}"/>`);
  return { svg: `<g class="iso-solid">${out.join("")}</g>` };
}
function bucketFront() {
  const { cx, cy, rTop, z, h } = BUCKET;
  const out = [];
  // borde enrollado
  out.push(L(k.ring(cx, cy, rTop, z + h, P, 72), { tone: "hi" }));
  out.push(L(k.ring(cx, cy, rTop - 1.6, z + h, P, 72), { tone: "lo" }));
  // asa: semicírculo sobre el balde, orejas a ±y
  const top = z + h;
  const ears = [[cx, cy - rTop, top - 6], [cx, cy + rTop, top - 6]];
  const arc = [...Array(25)].map((_, i) => { const a = (i / 24) * Math.PI; return at([cx - 6, cy - Math.cos(a) * rTop, top - 6 + Math.sin(a) * 30]); });
  out.push(`<path class="iso-line" data-tone="mid" style="stroke-width:1.6" d="${pathOf(arc)}"/>`);
  out.push(D(ears.map(([x, y, zz]) => at([x - 6, y, zz])), { size: 1.4, tone: "hi" }));
  return out.join("");
}

// Manguera de ordeño sobre un poste, con boquilla encima del balde
export const NOZZLE = [-246, -14, 176];
function milkPost() {
  const out = [];
  const base = [-312, -66];
  out.push(S(k.cylinder(base[0], base[1], 11, 8, 4, P, 28, 0.6), { tone: "mid" }));
  out.push(D(k.corners({ x: base[0] - 8, y: base[1] - 8, w: 16, d: 16 }, 2).map(([x, y]) => at([x, y, 12])), { size: 0.45 }));
  out.push(S(k.cylinder(base[0], base[1], 3.6, 12, 178, P, 20), { tone: "mid", crease: "none" }));
  out.push(L([60, 120].map((zz) => k.sideArc(base[0], base[1], 3.6, zz, P, 12)).join(""), { tone: "faint" }));
  // brazo horizontal (caja delgada a lo largo de x/y)
  const arm = { x: base[0] - 4, y: base[1] - 3, w: NOZZLE[0] - base[0] + 8, d: 6, r: 2 };
  out.push(S(k.slabOf(arm, 186, 5, P, 3, 0.4), { tone: "mid" }));
  const arm2 = { x: NOZZLE[0] - 3, y: base[1] - 3, w: 6, d: NOZZLE[1] - base[1] + 6, r: 2 };
  out.push(S(k.slabOf(arm2, 186, 5, P, 3, 0.4), { tone: "mid" }));
  out.push(S(k.cylinder(base[0], base[1], 5, 184, 9, P, 20), { tone: "mid" }));
  out.push(L(k.knurl(base[0], base[1], 5, 185, 192, 16, P), { tone: "lo" }));
  // boquilla
  out.push(S(k.cylinder(NOZZLE[0], NOZZLE[1], 4.5, NOZZLE[2] + 2, 8, P, 20), { tone: "mid" }));
  out.push(S(k.cylinder(NOZZLE[0], NOZZLE[1], 2.6, NOZZLE[2], 2.2, P, 16), { tone: "hi" }));
  // válvula de mariposa
  out.push(S(k.slabOf({ x: NOZZLE[0] + 4, y: NOZZLE[1] - 1.5, w: 10, d: 3, r: 1 }, NOZZLE[2] + 5, 2, P, 2), { tone: "mid", crease: "none" }));
  return out.join("");
}

// ---------- Protoboard ----------
function breadboard() {
  const out = [halo(BB, 0, BB_H, 5)];
  out.push(S(k.slabOf(BB, 0, BB_H, P, 4, 0.8), { tone: "hi", crease: "lo" }));
  // canal central y rieles
  out.push(`<path class="canal" d="${onTopZ([[BB.x + 4, -2.2], [BB.x + BB.w - 4, -2.2], [BB.x + BB.w - 4, 2.2], [BB.x + 4, 2.2]], BB_H + 0.05)}"/>`);
  for (const [y, tone] of [[-66.5, "blue"], [-58, "red"], [58, "blue"], [66.5, "red"]]) {
    out.push(L(k.lineOnTop([BB.x + 6, y], [BB.x + BB.w - 6, y], BB_H, P), { tone }));
  }
  // agujeros
  const holes = [];
  for (let x = BB.x + 8; x <= BB.x + BB.w - 8; x += PITCH) {
    for (const y of [-63.5, -61, 61, 63.5]) holes.push(at([x, y > 0 ? y : y, BB_H]));
    for (let j = 0; j < 5; j++) {
      holes.push(at([x, 8 + j * PITCH * 0.95 + 1, BB_H]));
      holes.push(at([x, -8 - j * PITCH * 0.95 - 1, BB_H]));
    }
  }
  out.push(D(holes, { size: 0.55, tone: "lo" }));
  return out.join("");
}

function esp32() {
  const out = [];
  // tiras de pines (plástico negro)
  for (const y of [-25, 21]) {
    out.push(S(k.slabOf({ x: pinX(18) - 3, y, w: 18 * PITCH + 6, d: 4, r: 0.5 }, BB_H, PCB_Z - BB_H, P, 2), { tone: "lo", crease: "none" }));
  }
  out.push(`<path class="iso-halo" d="${k.haloOf(PCB, BB_H, 0.1, P)}" style="filter:blur(4px);opacity:.55"/>`);
  out.push(S(k.slabOf(PCB, PCB_Z, PCB_T, P, 3, 0.6), { tone: "mid", className: "pcb" }));
  const top = PCB_Z + PCB_T;
  // pines (puntos dorados) y anillos
  const pinsF = PINES_FRENTE.map((_, i) => [pinX(i), 22.6]);
  const pinsB = PINES_ATRAS.map((_, i) => [pinX(i), -22.6]);
  out.push(L([...pinsF, ...pinsB].map(([x, y]) => k.ring(x, y, 1.5, top, P, 10)).join(""), { tone: "mid" }));
  out.push(D([...pinsF, ...pinsB].map(([x, y]) => at([x, y, top])), { size: 0.6, tone: "hi" }));
  // módulo ESP-WROOM-32: PCB del módulo + blindaje metálico + antena
  const mod = { x: -10, y: -18, w: 52, d: 36, r: 1 };
  out.push(S(k.slabOf(mod, top, 1, P, 2), { tone: "lo", crease: "none" }));
  const can = { x: -8, y: -16, w: 36, d: 32, r: 1.2 };
  out.push(S(k.slabOf(can, top + 1, 4.4, P, 2, 0.5), { tone: "hi", crease: "lo", className: "blindaje" }));
  out.push(L(k.planOutline(k.insetPlan(can, 2.4), top + 5.4, P, 2), { tone: "faint" }));
  out.push(k.faceTextSvg(k.topMatrix([-4, -3], top + 5.4, P, "x"), "ESP32-WROOM-32", { size: 3.6, tone: "mid" }));
  out.push(k.faceTextSvg(k.topMatrix([-4, 3.5], top + 5.4, P, "x"), "Espressif", { size: 2.6, tone: "lo" }));
  // antena serpentina
  const ant = [];
  const ax0 = 31, ax1 = 40;
  for (let i = 0; i <= 8; i++) {
    const y = -14 + i * 3.5;
    ant.push([i % 2 ? ax1 : ax0, y], [i % 2 ? ax1 : ax0, y + 3.5]);
  }
  out.push(`<path class="iso-line antena" data-tone="hi" d="${pathOf(ant.slice(0, -1).map(([x, y]) => at([x, y, top + 1])))}" data-free=""/>`);
  // conector USB
  out.push(S(k.slabOf({ x: -76, y: -7, w: 13, d: 14, r: 1 }, top, 5.5, P, 2, 0.4), { tone: "hi", crease: "lo" }));
  // botones EN y BOOT
  for (const y of [-17, 17]) {
    out.push(S(k.slabOf({ x: -62, y: y - 3, w: 7, d: 6, r: 0.6 }, top, 2.6, P, 2), { tone: "mid" }));
    out.push(S(k.cylinder(-58.5, y, 1.7, top + 2.6, 1.2, P, 12), { tone: "lo" }));
  }
  // regulador AMS1117 con pestaña
  out.push(S(k.slabOf({ x: -46, y: -14, w: 12, d: 8, r: 0.4 }, top, 3.2, P, 2), { tone: "lo" }));
  out.push(S(k.slabOf({ x: -46, y: -16.5, w: 12, d: 2.5, r: 0.3 }, top, 1.2, P, 2), { tone: "mid", crease: "none" }));
  // chip USB-UART CP2102
  out.push(S(k.slabOf({ x: -48, y: 2, w: 10, d: 10, r: 0.4 }, top, 1.6, P, 2), { tone: "lo" }));
  out.push(D([at([-46.5, 3.5, top + 1.6])], { size: 0.35 }));
  // condensadores SMD
  for (const [x, y] of [[-30, -12], [-30, 9], [-22, 12]]) out.push(S(k.slabOf({ x, y, w: 4, d: 2.4, r: 0.3 }, top, 1.4, P, 1), { tone: "mid", crease: "none" }));
  // LED de encendido (rojo) — siempre prendido
  out.push(`<circle class="led-power" cx="${r1(at([-36, 14, top + 0.8])[0])}" cy="${r1(at([-36, 14, top + 0.8])[1])}" r="1.6"/>`);
  out.push(S(k.slabOf({ x: -37.5, y: 12.8, w: 3, d: 2.4, r: 0.3 }, top, 0.8, P, 1), { tone: "mid", crease: "none" }));
  return out.join("");
}

// LED de 5 mm: base con reborde, cuerpo y domo. data-led para encenderlo en vivo.
function led(x, y, color, name) {
  const out = [];
  const z = BB_H;
  out.push(L(k.rise([x - 1.3, y], z, z + 3, P) + k.rise([x + 1.3, y], z, z + 3, P), { tone: "mid" }));
  out.push(`<g data-led="${name}" class="led" style="--led:${color}">`);
  out.push(S(k.cylinder(x, y, 6.2, z + 3, 1.4, P, 32), { tone: "hi", className: "led-body" }));
  out.push(S(k.cylinder(x, y, 5.4, z + 4.4, 7, P, 32), { tone: "hi", className: "led-body" }));
  // domo: tres discos decrecientes
  out.push(S(k.cylinder(x, y, 4.8, z + 11.4, 1.6, P, 28), { tone: "hi", className: "led-body", crease: "none" }));
  out.push(S(k.cylinder(x, y, 3.6, z + 13, 1.2, P, 24), { tone: "hi", className: "led-body", crease: "none" }));
  out.push(S(k.cylinder(x, y, 2, z + 14.2, 0.6, P, 16), { tone: "hi", className: "led-body", crease: "none" }));
  const c = at([x, y, z + 10]);
  out.push(`<circle class="led-glow" cx="${r1(c[0])}" cy="${r1(c[1])}" r="26"/>`);
  out.push(`</g>`);
  return out.join("");
}

// Resistencia de 220 Ω parada (bandas rojo-rojo-marrón-dorado)
function resistor(x, y) {
  const out = [];
  const z = BB_H;
  out.push(L(k.rise([x, y], z, z + 3, P), { tone: "mid" }));
  out.push(S(k.cylinder(x, y, 2.6, z + 3, 11, P, 20), { tone: "hi", className: "resistencia" }));
  const bands = [["#c0392b", z + 5], ["#c0392b", z + 7.2], ["#7b4a1e", z + 9.4], ["#c9a227", z + 12]];
  for (const [color, zz] of bands) out.push(`<path class="banda" style="stroke:${color}" d="${k.sideArc(x, y, 2.65, zz, P, 16)}"/>`);
  // pata superior que vuelve a la protoboard por detrás
  const leg = [at([x, y, z + 14]), at([x, y, z + 17]), at([x, y - 5.6, z + 17]), at([x, y - 5.6, z])];
  out.push(`<path class="iso-line" data-tone="mid" d="${pathOf(leg)}"/>`);
  return out.join("");
}

export const BUZ = [-52, 54];
function buzzer() {
  const [x, y] = BUZ;
  const out = [];
  out.push(`<path class="iso-halo" d="${k.haloOf({ x: x - 12, y: y - 12, w: 24, d: 24, r: 12 }, BB_H, 0.1, P)}" style="filter:blur(3px);opacity:.6"/>`);
  out.push(`<g data-part="buzzer">`);
  out.push(S(k.cylinder(x, y, 12, BB_H, 10, P, 40, 0.6), { tone: "lo", crease: "mid", className: "buzzer" }));
  out.push(L(k.ring(x, y, 9.2, BB_H + 10, P, 40), { tone: "mid" }));
  out.push(S(k.cylinder(x, y, 2.4, BB_H + 10, 0.3, P, 16), { tone: "lo", crease: "none" }));
  out.push(`<path class="hueco" d="${k.ring(x, y, 2, BB_H + 10.3, P, 16)}Z"/>`);
  out.push(D([at([x + 6, y - 6, BB_H + 10])], { size: 0.5, tone: "hi" }));
  out.push(k.faceTextSvg(k.topMatrix([x - 4, y + 7.5], BB_H + 10, P, "x"), "+", { size: 3.4, tone: "mid" }));
  out.push(`</g>`);
  return out.join("");
}

export const BTN = [-84, 50];
function pushButton() {
  const [x, y] = BTN;
  const out = [];
  const base = { x: x - 12, y: y - 12, w: 24, d: 24, r: 1.2 };
  out.push(`<path class="iso-halo" d="${k.haloOf(base, BB_H, 0.1, P)}" style="filter:blur(3px);opacity:.6"/>`);
  for (const [lx, ly] of k.corners(base, 3)) out.push(L(k.rise([lx, ly + (ly > y ? 1.5 : -1.5)], BB_H, BB_H + 2, P), { tone: "mid" }));
  out.push(S(k.slabOf(base, BB_H + 0.5, 7, P, 2, 0.6), { tone: "lo", crease: "mid" }));
  const plate = k.insetPlan(base, 1.2);
  out.push(S(k.slabOf(plate, BB_H + 7.5, 0.8, P, 2), { tone: "hi", crease: "none", className: "metal" }));
  out.push(D(k.corners(plate, 2.2).map(([px, py]) => at([px, py, BB_H + 8.3])), { size: 0.55, tone: "mid" }));
  out.push(`<g data-part="boton-tapa" style="cursor:pointer">`);
  out.push(S(k.cylinder(x, y, 8.2, BB_H + 8.3, 3, P, 32), { tone: "mid", className: "boton-cuello" }));
  out.push(S(k.cylinder(x, y, 7.4, BB_H + 11.3, 4.6, P, 32, 0.8), { tone: "hi", className: "boton-azul" }));
  out.push(L(k.knurl(x, y, 7.4, BB_H + 11.6, BB_H + 15.5, 22, P, 0.3), { tone: "lo" }));
  out.push(`</g>`);
  return out.join("");
}

// HX711: módulo verde sobre la protoboard, detrás del USB
const HXM = { x: -106, y: -54, w: 46, d: 30, r: 1 };
export const HX_PINS = { GND: -36, DT: -42, SCK: -48, VCC: -54 + 2 };
function hx711() {
  const out = [];
  const z = BB_H + 6;
  out.push(S(k.slabOf({ x: HXM.x + HXM.w - 5, y: HXM.y + 1, w: 4, d: HXM.d - 2, r: 0.4 }, BB_H, 6, P, 1), { tone: "lo", crease: "none" }));
  out.push(S(k.slabOf({ x: HXM.x + 2, y: HXM.y + 1, w: 4, d: HXM.d - 2, r: 0.4 }, BB_H, 6, P, 1), { tone: "lo", crease: "none" }));
  out.push(S(k.slabOf(HXM, z, 1.8, P, 2, 0.4), { tone: "mid", className: "pcb-hx" }));
  const top = z + 1.8;
  // chip SOP-16
  const chip = { x: HXM.x + 14, y: HXM.y + 9, w: 16, d: 12, r: 0.4 };
  out.push(S(k.slabOf(chip, top, 2.2, P, 2), { tone: "lo" }));
  const legs = [];
  for (let i = 0; i < 8; i++) {
    const lx = chip.x + 1.5 + i * 1.85;
    legs.push(k.lineOnTop([lx, chip.y - 1.6], [lx, chip.y], top + 0.1, P), k.lineOnTop([lx, chip.y + chip.d], [lx, chip.y + chip.d + 1.6], top + 0.1, P));
  }
  out.push(L(legs.join(""), { tone: "mid" }));
  out.push(D([at([chip.x + 2, chip.y + 2, top + 2.2])], { size: 0.4 }));
  out.push(k.faceTextSvg(k.topMatrix([chip.x + 2.4, chip.y + 7.4], top + 2.2, P, "x"), "HX711", { size: 3, tone: "mid" }));
  // pines de salida (lado +x) y de la celda (lado -x)
  const outPins = Object.values(HX_PINS).map((y) => [HXM.x + HXM.w - 3, y]);
  const cellPins = [-51, -45, -39, -33].map((y) => [HXM.x + 4, y + 2]);
  out.push(L([...outPins, ...cellPins].map(([x, y]) => k.ring(x, y, 1.4, top, P, 10)).join(""), { tone: "mid" }));
  out.push(D([...outPins, ...cellPins].map(([x, y]) => at([x, y, top])), { size: 0.55, tone: "hi" }));
  // condensadores
  for (const [x, y] of [[HXM.x + 34, HXM.y + 6], [HXM.x + 34, HXM.y + 22]]) out.push(S(k.slabOf({ x, y, w: 3.2, d: 2, r: 0.3 }, top, 1.2, P, 1), { tone: "hi", crease: "none" }));
  return out.join("");
}

// ---------- Vaca ----------
function cowBack() {
  const out = [];
  const { body, bodyZ, bodyH } = COW;
  out.push(`<path class="iso-halo" d="${k.haloOf(k.insetPlan(body, -6), 6, 0.1, P)}" style="filter:blur(7px)"/>`);
  // patas: traseras (y negativa) primero
  const legs = byDepth([[208, -12], [286, -12], [208, 12], [286, 12]]);
  for (const [x, y] of legs) {
    out.push(S(k.cylinder(x, y, 7.4, 6, 7, P, 24, 0.5), { tone: "lo", className: "pezuna" }));
    out.push(S(k.cylinder(x, y, 6.6, 13, bodyZ - 13 + 4, P, 24), { tone: "hi", crease: "none" }));
    out.push(L(k.sideArc(x, y, 6.6, 26, P, 12), { tone: "faint" }));
  }
  // ubre
  out.push(S(k.cylinder(266, 0, 11, bodyZ - 9, 10, P, 28), { tone: "hi", className: "ubre" }));
  for (const [x, y] of [[260, -5], [272, -5], [260, 5], [272, 5]]) out.push(S(k.cylinder(x, y, 1.8, bodyZ - 15, 6, P, 12), { tone: "hi", className: "ubre" }));
  // cola
  out.push(S(k.slabOf({ x: body.x + body.w - 1, y: -2, w: 4, d: 4, r: 1.5 }, bodyZ + 6, bodyH - 8, P, 2), { tone: "hi" }));
  out.push(S(k.cylinder(body.x + body.w + 1, 0, 3.6, bodyZ - 4, 12, P, 16), { tone: "lo", className: "mancha-solid" }));
  // cuerpo
  out.push(S(k.slabOf(body, bodyZ, bodyH, P, 10, 1.2), { tone: "hi", crease: "faint", className: "vaca" }));
  // manchas en la cara frontal (+y) y arriba
  const fy = body.y + body.d;
  const spots = [blob(230, 78, 12, 10, 1), blob(268, 66, 9, 7, 2.5), blob(290, 84, 5, 6, 4)];
  for (const s of spots) out.push(`<path class="mancha" d="${onFaceY(s.map(([x, z]) => [x, Math.min(Math.max(z, bodyZ + 1.5), bodyZ + bodyH - 1.5)]), fy)}"/>`);
  const spotsTop = [blob(250, -6, 16, 10, 3), blob(212, 12, 8, 7, 5)];
  for (const s of spotsTop) out.push(`<path class="mancha" d="${onTopZ(s, bodyZ + bodyH)}"/>`);
  // anca y paleta (huesos marcados)
  out.push(L(k.lineOnTop([290, -18], [290, 18], bodyZ + bodyH, P), { tone: "faint" }));
  return out.join("");
}

// Cabeza, cuello y collar: grupo que se balancea con la aceleración
function cowHead() {
  const out = [];
  const z0 = 74;
  // oreja lejana
  out.push(S(k.slabOf({ x: 156, y: -27, w: 9, d: 13, r: 3 }, 104, 4, P, 3), { tone: "hi" }));
  // cuello
  out.push(S(k.slabOf({ x: 166, y: -15, w: 40, d: 30, r: 9 }, z0 - 6, 36, P, 8, 0.8), { tone: "hi", className: "vaca" }));
  // collar (correa) alrededor del cuello
  const strap = { x: COLLAR_X - 4, y: -17.4, w: 8, d: 34.8, r: 3 };
  out.push(S(k.slabOf(strap, z0 - 8, 40, P, 4, 0.5), { tone: "mid", className: "collar" }));
  out.push(D([at([COLLAR_X, 17.4, z0 + 26]), at([COLLAR_X, 17.4, z0 + 2])], { size: 0.6, tone: "hi" }));
  // hebilla
  out.push(S(k.slabOf({ x: COLLAR_X - 5, y: 14, w: 10, d: 4.6, r: 1 }, z0 + 10, 9, P, 2, 0.4), { tone: "hi", className: "metal" }));
  // cabeza
  out.push(S(k.slabOf({ x: 138, y: -13, w: 34, d: 26, r: 7 }, 84, 30, P, 8, 0.8), { tone: "hi", className: "vaca" }));
  out.push(`<path class="mancha" d="${onFaceY(blob(160, 103, 6, 5, 7), 13)}"/>`);
  // hocico
  out.push(S(k.slabOf({ x: 126, y: -11, w: 20, d: 22, r: 6 }, 82, 17, P, 6, 0.6), { tone: "hi", className: "hocico" }));
  out.push(D([at([126, -5, 91]), at([126, 5, 91])], { size: 1.3, tone: "hi" }));
  // ojo
  out.push(D([at([150, 13, 106])], { size: 1.8, tone: "hi" }));
  // cuernos
  for (const y of [-8, 8]) out.push(S(k.cylinder(160, y, 2.4, 114, 6, P, 14), { tone: "hi", className: "cuerno" }), S(k.cylinder(160, y, 1.5, 120, 3, P, 12), { tone: "hi", className: "cuerno" }));
  // oreja cercana
  out.push(S(k.slabOf({ x: 156, y: 14, w: 9, d: 13, r: 3 }, 104, 4, P, 3), { tone: "hi" }));
  // carcasa del MPU6050 colgando bajo el collar (contrapeso)
  const box = { x: COLLAR_X - 9, y: -10, w: 18, d: 20, r: 2 };
  out.push(S(k.slabOf(box, GLAND[2] + 4, z0 - 8 - GLAND[2] - 4, P, 3, 0.6), { tone: "mid", className: "carcasa-mpu" }));
  out.push(D(k.corners(box, 2.6).map(([x, y]) => at([x, y, z0 - 8])), { size: 0.5 }));
  // ventana con el módulo GY-521 visible en la cara frontal
  const win = [[COLLAR_X - 6, GLAND[2] + 7], [COLLAR_X + 6, GLAND[2] + 7], [COLLAR_X + 6, z0 - 11], [COLLAR_X - 6, z0 - 11]];
  out.push(`<path class="mpu-ventana" d="${onFaceY(win, 10.05)}"/>`);
  out.push(`<path class="mpu-chip" data-part="mpu-chip" d="${onFaceY([[COLLAR_X - 2.5, GLAND[2] + 9], [COLLAR_X + 2.5, GLAND[2] + 9], [COLLAR_X + 2.5, GLAND[2] + 13], [COLLAR_X - 2.5, GLAND[2] + 13]], 10.1)}"/>`);
  // prensaestopa del cable
  out.push(S(k.cylinder(GLAND[0], GLAND[1], 2.6, GLAND[2], 4, P, 16), { tone: "lo" }));
  return out.join("");
}

function plinth() {
  const out = [halo(PLINTH, 0, 6, 6)];
  out.push(S(k.slabOf(PLINTH, 0, 6, P, 6, 1), { tone: "mid" }));
  out.push(L(k.planOutline(k.insetPlan(PLINTH, 5), 6, P), { tone: "faint" }));
  const sc = k.corners(PLINTH, 9);
  out.push(L(sc.map(([x, y]) => k.ring(x, y, 2.2, 6, P, 14)).join(""), { tone: "lo" }));
  out.push(D(sc.map(([x, y]) => at([x, y, 6])), { size: 0.6 }));
  const plate = { x: 280, y: 52, w: 46, d: 26, r: 1.5 };
  out.push(S(k.slabOf(plate, 6, 0.8, P, 3), { tone: "lo", crease: "none" }));
  out.push(L(k.planOutline(k.insetPlan(plate, 2), 6.8, P, 3), { tone: "faint" }));
  out.push(k.faceTextSvg(k.topMatrix([plate.x + 5, plate.y + 10], 6.8, P, "x"), "COLLAR", { size: 5.2, tone: "mid" }));
  [16, 21].forEach((y, i) => out.push(L(k.lineOnTop([plate.x + 5, plate.y + y], [plate.x + (i ? 24 : 34), plate.y + y], 6.8, P), { tone: "lo", free: true })));
  return out.join("");
}

// ---------- Cables ----------
// Cada cable: id, puntos 3D, color, texto de ayuda (pin y protocolo).
const BBZ = BB_H + 0.9;
export const CABLES = [];
function cable(id, pts, color, info, { lifted = false, width = 1.9 } = {}) {
  CABLES.push({ id, pts, color, info, lifted, width });
}
// LEDs, buzzer, botón (cara frontal, columna +y)
const LEDX = { rojo: 10, amarillo: 30, verde: 50 };
const RES_Y = 47, LED_Y = 58;
const front = (name, yLevel, tx, ty, color, info) =>
  cable(name, [[frente(name), HOLE_Y, BBZ], [frente(name), yLevel, BBZ], [tx, yLevel, BBZ], [tx, ty, BBZ]], color, info);
front("25", 34, LEDX.verde, RES_Y - 2.6, "#2fbf71", { pin: "GPIO 25", que: "LED verde (por resistencia de 220 Ω)", proto: "Salida digital · semaforo.verde", cfg: "PIN_LED_VERDE = 25" });
front("26", 38, LEDX.amarillo, RES_Y - 2.6, "#e0b000", { pin: "GPIO 26", que: "LED amarillo (por resistencia de 220 Ω)", proto: "Salida digital · semaforo.amarillo", cfg: "PIN_LED_AMARILLO = 26" });
front("27", 42, LEDX.rojo, RES_Y - 2.6, "#e5484d", { pin: "GPIO 27", que: "LED rojo (por resistencia de 220 Ω)", proto: "Salida digital · semaforo.rojo", cfg: "PIN_LED_ROJO = 27" });
front("14", 42.5 + 2, BUZ[0], BUZ[1] - 12, "#8e6bd8", { pin: "GPIO 14", que: "Buzzer (+)", proto: "PWM 2000 Hz, ciclo útil 50 % · Buzzer", cfg: "PIN_BUZZER = 14" });
CABLES[CABLES.length - 1].pts = [[frente("14"), HOLE_Y, BBZ], [frente("14"), 44.5, BBZ], [BUZ[0] + 6, 44.5, BBZ], [BUZ[0] + 6, BUZ[1] - 10.4, BBZ]];
cable("13", [[frente("13"), HOLE_Y, BBZ], [frente("13"), 34, BBZ], [BTN[0] + 6, 34, BBZ], [BTN[0] + 6, BTN[1] - 12, BBZ]], "#3e8bff", { pin: "GPIO 13", que: "Pulsador (el otro extremo va a GND)", proto: "Entrada con pull-up interna · presionado = 0", cfg: "PIN_BOTON = 13" });
cable("gnd-f", [[frente("GND"), HOLE_Y, BBZ], [frente("GND"), HOLE_Y, 22], [frente("GND"), 58, 22], [frente("GND"), 58, BBZ]], "#444", { pin: "GND", que: "Riel de tierra de LEDs, buzzer y pulsador", proto: "Tierra común", cfg: "" }, { lifted: true });
// HX711 (columna trasera, hacia el módulo de la izquierda)
cable("4", [[atras("4"), -HOLE_Y, BBZ], [atras("4"), HX_PINS.DT, BBZ], [HXM.x + HXM.w - 3, HX_PINS.DT, BBZ + 7.4]], "#ff9f1a", { pin: "GPIO 4", que: "HX711 · DT (datos)", proto: "Entrada digital: DT baja a 0 cuando hay lectura lista", cfg: "PIN_HX711_DT = 4" });
cable("5", [[atras("5"), -HOLE_Y, BBZ], [atras("5"), HX_PINS.SCK, BBZ], [HXM.x + HXM.w - 3, HX_PINS.SCK, BBZ + 7.4]], "#00b5c8", { pin: "GPIO 5", que: "HX711 · SCK (reloj)", proto: "Salida digital: 24 + 1 pulsos por lectura", cfg: "PIN_HX711_SCK = 5" });
// I2C hacia la vaca (derecha)
const I2C_X = 104;
cable("21", [[atras("21"), -HOLE_Y, BBZ], [atras("21"), -40, BBZ], [I2C_X + 4, -40, BBZ]], "#3e63dd", { pin: "GPIO 21", que: "MPU6050 · SDA (datos)", proto: "I2C a 400 kHz, dirección 0x68", cfg: "PIN_I2C_SDA = 21" });
cable("22", [[atras("22"), -HOLE_Y, BBZ], [atras("22"), -36, BBZ], [I2C_X + 4, -36, BBZ]], "#e5a50a", { pin: "GPIO 22", que: "MPU6050 · SCL (reloj)", proto: "I2C a 400 kHz (lo genera la ESP32)", cfg: "PIN_I2C_SCL = 22" });
cable("gnd-b", [[atras("GND"), -HOLE_Y, BBZ], [atras("GND"), -32.5, BBZ], [I2C_X + 4, -32.5, BBZ]], "#444", { pin: "GND", que: "Tierra del MPU6050", proto: "Tierra común", cfg: "" });
cable("3v3", [[frente("3V3"), HOLE_Y, BBZ], [frente("3V3"), HOLE_Y, 26], [frente("3V3") + 6, 0, 30], [frente("3V3") + 14, -43.5, 26], [I2C_X + 4, -43.5, BBZ]], "#c0392b", { pin: "3V3", que: "Alimentación del MPU6050", proto: "3.3 V", cfg: "" }, { lifted: true });
// mazo hacia la vaca: sale de la protoboard y sube al collar
export const HARNESS_START = [I2C_X + 8, -38, BBZ];
export const HARNESS_ROUTE = [[I2C_X + 8, -38, BBZ], [116, -38, BBZ], [120, -38, 1.5], [128, -38, 1.5], [131, -38, 7], [168, -38, 7], [GLAND[0], -12, 7], [GLAND[0], 0, 7]];
// Celda de carga → HX711
const CELL_WIRES = [["#e5484d", "E+"], ["#222", "E−"], ["#eee", "A−"], ["#30a46c", "A+"]];
export const CELL_CABLE = CELL_WIRES.map(([color, name], i) => ({
  color, name,
  pts: [[HXM.x + 4, -49 + i * 6, BB_H + 8], [HXM.x - 3, -49 + i * 6, BB_H + 8], [HXM.x - 10, -49 + i * 6, 1.2], [-150, -40 + i * 2.2, 1.2], [-180, -26 + i * 2.2, 8.5], [-278, -26 + i * 2.2, 8.5], [-286, -15, 14 + i * 2]],
}));

export function cableSvg(c) {
  const d = pathOf(c.pts.map(at));
  const ends = [c.pts[0], c.pts[c.pts.length - 1]].map(at);
  return `<g class="cable${c.lifted ? " cable-alto" : ""}" data-cable="${c.id}" style="--c:${c.color};--w:${c.width}">` +
    `<path class="casing" d="${d}"/><path class="core" d="${d}"/><path class="pulso" d="${d}"/><path class="hit" d="${d}"/>` +
    ends.map(([x, y]) => `<circle class="punta" cx="${r1(x)}" cy="${r1(y)}" r="1.5"/>`).join("") + `</g>`;
}
export const harnessD = (pts) => pathOf(pts.map(at));

// ---------- Ondas WiFi (antena) ----------
export const ANTENNA = at([36, 0, PCB_Z + PCB_T + 2]);

// Vistas para el zoom: rectángulo de pantalla que encierra puntos del mundo
function vista(puntos, pad = 18) {
  const ps = puntos.map(at);
  const xs = ps.map((p) => p[0]), ys = ps.map((p) => p[1]);
  let x0 = Math.min(...xs) - pad, x1 = Math.max(...xs) + pad, y0 = Math.min(...ys) - pad, y1 = Math.max(...ys) + pad;
  // mantener la proporción del lienzo
  const r = W / H;
  if ((x1 - x0) / (y1 - y0) < r) { const w = (y1 - y0) * r; const c = (x0 + x1) / 2; x0 = c - w / 2; x1 = c + w / 2; }
  else { const h = (x1 - x0) / r; const c = (y0 + y1) / 2; y0 = c - h / 2; y1 = c + h / 2; }
  return [x0, y0, x1 - x0, y1 - y0].map((v) => Math.round(v * 10) / 10);
}
export const VISTAS = {
  completa: [0, 0, W, H],
  protoboard: vista([...k.boxCorners(BB, 0, 30)], 10),
  collar: vista([...k.boxCorners({ x: 20, y: -72, w: 300, d: 144 }, 0, 130)], 6),
  balanza: vista([...k.boxCorners({ x: -334, y: -60, w: 280, d: 150 }, 0, 0), [-246, -14, 182], [-238, 48, 134]], 4),
};

// ---------- Ensamblado ----------
export function build() {
  const resistors = ["rojo", "amarillo", "verde"].map((n) => resistor(LEDX[n], RES_Y)).join("");
  const leds = ["rojo", "amarillo", "verde"].map((n) => led(LEDX[n], LED_Y, { rojo: "#ff4040", amarillo: "#ffc21a", verde: "#2fdc7a" }[n], n)).join("");
  const flat = CABLES.filter((c) => !c.lifted);
  const lifted = CABLES.filter((c) => c.lifted);
  const cellCable = CELL_CABLE.map((w) => `<g class="cable" data-cable="celda-${w.name}" style="--c:${w.color};--w:1.4"><path class="casing" d="${pathOf(w.pts.map(at))}"/><path class="core" d="${pathOf(w.pts.map(at))}"/><path class="hit" d="${pathOf(w.pts.map(at))}"/></g>`).join("");
  const bucket = bucketBack();
  const body = [
    bench(),
    // izquierda: estación
    stationBase(),
    loadCell(),
    cellCable,
    milkPost().split("<!--front-->")[0],
    `<g data-part="plato">`,
    platform(),
    bucket.svg,
    `<g data-part="leche"></g>`,
    bucketFront(),
    `</g>`,
    `<path data-part="chorro" class="chorro" d=""/>`,
    // centro: protoboard
    breadboard(),
    hx711(),
    flat.map(cableSvg).join(""),
    esp32(),
    `<g data-part="wifi"></g>`,
    resistors,
    buzzer(),
    `<g data-part="ondas"></g>`,
    pushButton(),
    leds,
    lifted.map(cableSvg).join(""),
    // derecha: vaca
    plinth(),
    `<g class="cable mazo" data-cable="mpu"><path class="casing" data-part="mazo-a" d=""/><path class="core" data-part="mazo-b" d=""/><path class="pulso" data-part="mazo-c" d=""/><path class="hit" data-part="mazo-d" d=""/></g>`,
    cowBack(),
    `<g data-part="cabeza">${cowHead()}</g>`,
  ];
  return k.figureSvg({
    width: W,
    height: H,
    label: "Banco de pruebas: a la izquierda una balanza con celda de carga y un balde de leche; al centro una protoboard con la ESP32, el HX711, tres LEDs, un buzzer y un pulsador; a la derecha una vaca con un collar que lleva el MPU6050.",
    body,
  });
}

// Casco convexo (monotone chain)
function convexHull(points) {
  const pts = [...points].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const cross = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lower = [];
  for (const p of pts) { while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop(); lower.push(p); }
  const upper = [];
  for (const p of pts.reverse()) { while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop(); upper.push(p); }
  return lower.slice(0, -1).concat(upper.slice(0, -1));
}
