.pragma library

// One ambient behaviour per Pokémon type — eighteen of them, no reuse. Each
// entry is data, and Ambient.qml animates whatever it is handed, so a new
// effect is a row here rather than new QML.
//
//   count     shapes on screen at intensity 1.0
//   size      base px (each shape jitters ±40% around it)
//   duration  ms for one full cycle
//   opacity   peak opacity of a shape
//   motion    how it moves — see Ambient.qml
//               rise    bottom to top
//               fall    top to bottom
//               drift   left to right at a fixed height
//               hold    stays put and pulses
//               expand  ring blooming outward from a point
//               streak  long thin dash crossing fast
//               orbit   circles a point on the card
//               spiral  swirls inward and vanishes at the centre
//               strike  a bolt that flashes into place, then a long dark wait
//               zigzag  rises while tacking side to side
//               settle  falls, then piles up and fades at the floor
//   shape     "dot" | "ring" | "leaf" | "bar" (flying only) | "chip" | "bolt"
//   spread    px of lateral wander over the cycle
//   spin      degrees of rotation over the cycle

var BASE = {
  motes:    { count: 10, size: 3,  duration: 14000, opacity: 0.22, motion: "drift",  shape: "dot",  spread: 80,  spin: 0 },
  embers:   { count: 12, size: 3,  duration: 5000,  opacity: 0.75, motion: "rise",   shape: "dot",  spread: 90,  spin: 0 },
  bubbles:  { count: 12, size: 9,  duration: 9000,  opacity: 0.35, motion: "rise",   shape: "ring", spread: 90,  spin: 0 },
  // sparks is the quieter alternate for electric: `effect-electric = "sparks"`.
  sparks:   { count: 16, size: 3,  duration: 900,   opacity: 0.9,  motion: "hold",   shape: "bar",  spread: 0,   spin: 0 },
  leaves:   { count: 12, size: 6,  duration: 8000,  opacity: 0.6,  motion: "fall",   shape: "leaf", spread: 140, spin: 200 },
  flakes:   { count: 14, size: 3,  duration: 11000, opacity: 0.55, motion: "fall",   shape: "dot",  spread: 40,  spin: 0 },
  impact:   { count: 5,  size: 46, duration: 2600,  opacity: 0.3,  motion: "expand", shape: "ring", spread: 0,   spin: 0 },
  smog:     { count: 7,  size: 46, duration: 12000, opacity: 0.14, motion: "rise",   shape: "dot",  spread: 120, spin: 0 },
  grit:     { count: 16, size: 3,  duration: 5200,  opacity: 0.4,  motion: "settle", shape: "chip", spread: 30,  spin: 0 },
  gusts:    { count: 4,  size: 62, duration: 4600,  opacity: 0.12, motion: "streak", shape: "bar",  spread: 30,  spin: 0 },
  ripples:  { count: 4,  size: 90, duration: 5200,  opacity: 0.22, motion: "expand", shape: "ring", spread: 0,   spin: 0 },
  flit:     { count: 12, size: 3,  duration: 5200,  opacity: 0.6,  motion: "zigzag", shape: "dot",  spread: 70,  spin: 0 },
  rubble:   { count: 7,  size: 7,  duration: 13000, opacity: 0.5,  motion: "orbit",  shape: "chip", spread: 150, spin: 220 },
  wisps:    { count: 12, size: 38, duration: 14000, opacity: 0.13, motion: "drift",  shape: "dot",  spread: 60,  spin: 0 },
  vortex:   { count: 18, size: 6,  duration: 5200,  opacity: 0.85, motion: "spiral", shape: "dot",  spread: 270, spin: 0 },
  gloom:    { count: 5,  size: 130,duration: 9000,  opacity: 0.2,  motion: "hold",   shape: "dot",  spread: 0,   spin: 0 },
  plates:   { count: 8,  size: 26, duration: 5200,  opacity: 0.18, motion: "hold",   shape: "chip", spread: 0,   spin: 0 },
  twinkles: { count: 12, size: 3,  duration: 1600,  opacity: 0.85, motion: "hold",   shape: "dot",  spread: 0,   spin: 0 },

  // Electric's default. `sparks` above is its quieter alternate.
  strikes:  { count: 3,  size: 130,duration: 3000,  opacity: 0.9,  motion: "strike", shape: "bolt", spread: 0,   spin: 0 }
}

// Three takes on every effect, as multipliers rather than eighteen more hand
// written tables: calm is the tuned default, busy trades size for numbers and
// speed, bold does the opposite.
var VARIANTS = [
  { name: "calm",  count: 1.0, duration: 1.0,  size: 1.0 },
  { name: "busy",  count: 2.1, duration: 0.55, size: 0.7 },
  { name: "bold",  count: 0.5, duration: 1.7,  size: 1.9 }
]

function config(kind, variant) {
  var base = BASE[String(kind || "").toLowerCase()]
  if (!base) return null
  var index = Math.max(1, Math.min(VARIANTS.length, Math.round(Number(variant) || 1))) - 1
  var mod = VARIANTS[index]
  return {
    name: mod.name,
    count: Math.max(1, Math.round(base.count * mod.count)),
    size: Math.max(1, base.size * mod.size),
    duration: Math.max(200, Math.round(base.duration * mod.duration)),
    opacity: base.opacity,
    motion: base.motion,
    shape: base.shape,
    spread: base.spread,
    spin: base.spin
  }
}

