import QtQuick
import "Effects.js" as Effects

// Ambient motion behind the card contents, one behaviour per Pokémon type.
//
// Hand-rolled rather than QtQuick.Particles: a lock screen wants a dozen slow
// shapes, not a particle system, and this keeps the plugin to plain QtQuick
// with no extra imports. Every number comes from Effects.js; this file only
// knows how to move things.
Item {
  id: root

  // Any key in Effects.BASE, or "none".
  property string kind: "none"
  // 1 calm, 2 busy, 3 bold.
  property int variant: 1
  property color tint: "#ffffff"
  property real intensity: 1.0

  readonly property var config: Effects.config(kind, variant)
  readonly property int count: config ? Math.max(1, Math.round(config.count * intensity)) : 0

  clip: true
  visible: !!config && intensity > 0

  Repeater {
    model: root.count

    delegate: Item {
      id: shape
      required property int index

      // Deterministic-per-index jitter would repeat visibly across a row of
      // shapes; a random seed per shape is what makes the drift look natural.
      readonly property real seed: Math.random()
      readonly property real seedB: Math.random()
      readonly property var cfg: root.config
      readonly property int stagger: Math.round(seed * cfg.duration)
      readonly property int span: Math.round(cfg.duration * (0.75 + seedB * 0.5))
      readonly property string motion: cfg.motion

      // Travelling motions share one axis convention: `travel` is the axis the
      // shape crosses the card on, `wander` is the one it wobbles along.
      readonly property bool horizontal: motion === "drift" || motion === "streak"

      x: seedB * root.width
      width: 1
      height: 1

      Rectangle {
        id: dot
        visible: cfg.shape !== "bolt"
        anchors.centerIn: parent
        width: {
          var base = cfg.size * (0.6 + shape.seed * 0.8)
          if (cfg.shape === "bar") return base * 2.4
          return base
        }
        height: {
          if (cfg.shape === "leaf") return Math.max(2, width * 0.55)
          if (cfg.shape === "bar") return Math.max(1, cfg.size * 0.045)
          if (cfg.shape === "chip") return Math.max(2, width * 0.8)
          return width
        }
        radius: {
          if (cfg.shape === "chip") return 1
          if (cfg.shape === "leaf" || cfg.shape === "bar") return Math.max(1, height / 2)
          return width / 2
        }
        color: cfg.shape === "ring" ? "transparent" : root.tint
        border.width: cfg.shape === "ring" ? Math.max(1, Math.round(cfg.size / 12)) : 0
        border.color: root.tint
        opacity: 0
        rotation: cfg.spin !== 0 ? shape.seed * 90 : 0
        antialiasing: true
      }

      // rise / fall / drift / streak / settle: one traversal per cycle. `settle`
      // stops short of the floor so grains look like they land there.
      SequentialAnimation {
        running: root.visible && ["rise", "fall", "drift", "streak", "settle"].indexOf(shape.motion) >= 0
        loops: Animation.Infinite
        PauseAnimation { duration: shape.stagger }
        ScriptAction {
          script: {
            if (shape.horizontal) shape.y = shape.seed * root.height
            else shape.x = shape.seedB * root.width
          }
        }
        ParallelAnimation {
          NumberAnimation {
            target: shape
            property: shape.horizontal ? "x" : "y"
            from: {
              if (shape.motion === "fall" || shape.motion === "settle") return -cfg.size * 2
              if (shape.motion === "rise") return root.height + cfg.size
              return -cfg.size * 3
            }
            to: {
              if (shape.motion === "fall") return root.height + cfg.size
              // settle stops just short of the floor and stays there while it
              // fades, so grains look like they land rather than fall through.
              if (shape.motion === "settle") return root.height - cfg.size * (0.5 + shape.seed * 2.5)
              if (shape.motion === "rise") return -cfg.size * 2
              return root.width + cfg.size * 3
            }
            duration: shape.motion === "settle" ? Math.round(shape.span * 0.55) : shape.span
            easing.type: shape.motion === "settle" ? Easing.InQuad : Easing.Linear
          }
          NumberAnimation {
            target: shape
            property: shape.horizontal ? "y" : "x"
            to: shape.horizontal
              ? Math.max(0, Math.min(root.height, shape.y + (shape.seed - 0.5) * cfg.spread))
              : Math.max(0, Math.min(root.width, shape.x + (shape.seed - 0.5) * cfg.spread))
            duration: shape.span
            easing.type: Easing.InOutSine
          }
          NumberAnimation {
            target: dot; property: "rotation"
            to: dot.rotation + cfg.spin
            duration: shape.span
          }
          SequentialAnimation {
            NumberAnimation { target: dot; property: "opacity"; to: cfg.opacity; duration: Math.round(shape.span * 0.18) }
            PauseAnimation { duration: Math.round(shape.span * 0.64) }
            NumberAnimation { target: dot; property: "opacity"; to: 0; duration: Math.round(shape.span * 0.18) }
          }
        }
      }

      // zigzag: rises while tacking, for something alive rather than falling.
      SequentialAnimation {
        running: root.visible && shape.motion === "zigzag"
        loops: Animation.Infinite
        PauseAnimation { duration: shape.stagger }
        ScriptAction { script: shape.x = shape.seedB * root.width }
        ParallelAnimation {
          NumberAnimation {
            target: shape; property: "y"
            from: root.height + cfg.size; to: -cfg.size * 2
            duration: shape.span
            easing.type: Easing.Linear
          }
          SequentialAnimation {
            loops: 4
            NumberAnimation { target: shape; property: "x"; to: Math.min(root.width, shape.x + cfg.spread / 2); duration: Math.round(shape.span / 8); easing.type: Easing.InOutSine }
            NumberAnimation { target: shape; property: "x"; to: Math.max(0, shape.x - cfg.spread / 2); duration: Math.round(shape.span / 8); easing.type: Easing.InOutSine }
          }
          SequentialAnimation {
            NumberAnimation { target: dot; property: "opacity"; to: cfg.opacity; duration: Math.round(shape.span * 0.2) }
            PauseAnimation { duration: Math.round(shape.span * 0.6) }
            NumberAnimation { target: dot; property: "opacity"; to: 0; duration: Math.round(shape.span * 0.2) }
          }
        }
      }

      // expand: a ring blooming out of a point and fading, for shockwaves and
      // psychic ripples.
      SequentialAnimation {
        running: root.visible && shape.motion === "expand"
        loops: Animation.Infinite
        ScriptAction {
          script: {
            shape.x = shape.seedB * root.width
            shape.y = shape.seed * root.height
            dot.scale = 0.15
          }
        }
        PauseAnimation { duration: shape.stagger }
        ParallelAnimation {
          NumberAnimation { target: dot; property: "scale"; from: 0.15; to: 1.0; duration: shape.span; easing.type: Easing.OutQuad }
          SequentialAnimation {
            NumberAnimation { target: dot; property: "opacity"; to: cfg.opacity; duration: Math.round(shape.span * 0.25) }
            NumberAnimation { target: dot; property: "opacity"; to: 0; duration: Math.round(shape.span * 0.75) }
          }
        }
        PauseAnimation { duration: Math.round(shape.span * (0.3 + shape.seedB)) }
      }

      // orbit / spiral: the two radial motions. Rock's rubble circles a point
      // on the card at a steady radius; dragon's vortex swirls inward and
      // vanishes at the centre, then starts again from the rim.
      readonly property real centreX: root.width * (0.32 + shape.seedB * 0.36)
      readonly property real centreY: root.height * 0.5
      property real angle: shape.seed * Math.PI * 2
      property real radius: cfg.spread * (0.35 + shape.seed * 0.65)

      Binding {
        target: shape
        property: "x"
        when: shape.motion === "orbit" || shape.motion === "spiral"
        value: shape.centreX + Math.cos(shape.angle) * shape.radius
      }

      Binding {
        target: shape
        property: "y"
        when: shape.motion === "orbit" || shape.motion === "spiral"
        // Squashed circle: a true circle reads as a clock face, an ellipse
        // reads as something turning in space.
        value: shape.centreY + Math.sin(shape.angle) * shape.radius * 0.55
      }

      SequentialAnimation {
        running: root.visible && shape.motion === "orbit"
        loops: Animation.Infinite
        ParallelAnimation {
          NumberAnimation {
            target: shape; property: "angle"
            from: shape.seed * Math.PI * 2
            to: shape.seed * Math.PI * 2 + Math.PI * 2
            duration: shape.span
            easing.type: Easing.Linear
          }
          NumberAnimation { target: dot; property: "rotation"; to: dot.rotation + cfg.spin; duration: shape.span }
          SequentialAnimation {
            NumberAnimation { target: dot; property: "opacity"; to: cfg.opacity; duration: Math.round(shape.span * 0.15) }
            PauseAnimation { duration: Math.round(shape.span * 0.7) }
            NumberAnimation { target: dot; property: "opacity"; to: cfg.opacity * 0.35; duration: Math.round(shape.span * 0.15) }
          }
        }
      }

      SequentialAnimation {
        running: root.visible && shape.motion === "spiral"
        loops: Animation.Infinite
        PauseAnimation { duration: shape.stagger }
        ScriptAction { script: shape.radius = cfg.spread * (0.5 + shape.seedB * 0.5) }
        ParallelAnimation {
          NumberAnimation {
            target: shape; property: "angle"
            from: shape.seed * Math.PI * 2
            to: shape.seed * Math.PI * 2 + Math.PI * 3
            duration: shape.span
            easing.type: Easing.InQuad
          }
          NumberAnimation {
            target: shape; property: "radius"
            to: 4
            duration: shape.span
            easing.type: Easing.InQuad
          }
          SequentialAnimation {
            NumberAnimation { target: dot; property: "opacity"; to: cfg.opacity; duration: Math.round(shape.span * 0.25) }
            PauseAnimation { duration: Math.round(shape.span * 0.5) }
            NumberAnimation { target: dot; property: "opacity"; to: 0; duration: Math.round(shape.span * 0.25) }
          }
        }
      }

      // strike: a lightning bolt. The path is regenerated before every flash,
      // so no two strikes take the same route down the card, and the long dark
      // gap between them is what makes each one land.
      Loader {
        id: boltLoader
        active: cfg.shape === "bolt"
        width: Math.max(24, cfg.size * 0.35)
        height: cfg.size
        x: -width / 2
        y: -height / 2
        opacity: 0
        sourceComponent: boltCanvas
      }

      Component {
        id: boltCanvas

        Canvas {
          id: bolt
          anchors.fill: parent
          antialiasing: true

          property var joints: []

          function reroute() {
            var points = []
            var segments = 5 + Math.round(Math.random() * 2)
            for (var i = 0; i <= segments; i++) {
              points.push({
                x: width / 2 + (Math.random() - 0.5) * width * (i === 0 || i === segments ? 0.2 : 1.0),
                y: height * (i / segments)
              })
            }
            joints = points
            requestPaint()
          }

          onPaint: {
            var ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            if (joints.length < 2) return
            // Wide soft pass first, then the hot core on top.
            for (var pass = 0; pass < 2; pass++) {
              ctx.beginPath()
              ctx.lineWidth = pass === 0 ? 6 : 2
              ctx.globalAlpha = pass === 0 ? 0.25 : 1.0
              ctx.strokeStyle = root.tint
              ctx.lineJoin = "round"
              ctx.lineCap = "round"
              ctx.moveTo(joints[0].x, joints[0].y)
              for (var i = 1; i < joints.length; i++) ctx.lineTo(joints[i].x, joints[i].y)
              ctx.stroke()
            }
          }

          onWidthChanged: reroute()
          onHeightChanged: reroute()
          Component.onCompleted: reroute()
        }
      }

      SequentialAnimation {
        running: root.visible && shape.motion === "strike"
        loops: Animation.Infinite
        PauseAnimation { duration: shape.stagger }
        ScriptAction {
          script: {
            shape.x = root.width * (0.1 + Math.random() * 0.8)
            // Start above the card lip so the bolt reads as coming down into it.
            shape.y = root.height * (-0.05 + Math.random() * 0.3)
            if (boltLoader.item) boltLoader.item.reroute()
          }
        }
        // Two quick flashes, the way real lightning strikes twice.
        NumberAnimation { target: boltLoader; property: "opacity"; to: cfg.opacity; duration: 40 }
        NumberAnimation { target: boltLoader; property: "opacity"; to: 0.1; duration: 70 }
        NumberAnimation { target: boltLoader; property: "opacity"; to: cfg.opacity * 0.85; duration: 50 }
        NumberAnimation { target: boltLoader; property: "opacity"; to: 0; duration: 260 }
        PauseAnimation { duration: shape.span }
      }

      // hold: stays put and pulses — twinkles, and the electric sparks, which
      // are short bars blinking in place.
      SequentialAnimation {
        running: root.visible && shape.motion === "hold"
        loops: Animation.Infinite
        ScriptAction {
          script: {
            shape.x = Math.random() * root.width
            shape.y = Math.random() * root.height
            dot.rotation = cfg.shape === "bar" ? (Math.random() * 180 - 90) : dot.rotation
          }
        }
        PauseAnimation { duration: shape.stagger }
        NumberAnimation { target: dot; property: "opacity"; to: cfg.opacity; duration: Math.round(shape.span * 0.35) }
        NumberAnimation { target: dot; property: "opacity"; to: 0; duration: Math.round(shape.span * 0.45) }
        PauseAnimation { duration: Math.round(shape.span * (0.4 + shape.seedB)) }
      }
    }
  }
}
