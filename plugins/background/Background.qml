import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import Quickshell.Services.UPower
import Quickshell.Wayland
import QtQuick
import QtQuick.Effects
import QtQuick.Shapes
import qs.Commons
import qs.Ui

Item {
  id: root

  readonly property string home: Quickshell.env("HOME")
  readonly property string stateHome: home + "/.local/state"
  readonly property string currentBackgroundLink: stateHome + "/omarchy/current/background"

  property string currentBackground: ""
  property string displayedBackground: ""
  property string incomingBackground: ""
  property string oldBackground: ""
  property bool finishingTransition: false
  property int backgroundVersion: 0
  property int revealStartedVersion: -1
  property int pendingThemeVersion: -1
  property string pendingColorsRaw: ""
  property string pendingShellRaw: ""
  property real revealProgress: 1

  // ---------------------------------------------------------- ambient motion
  //
  // Everything below is additive: with no [background] tokens set, `kind` is
  // "none", Ambient renders nothing, and this behaves exactly like the stock
  // plugin it was cloned from.

  function token(key, fallback) {
    var value = Color.shellValues["background." + key]
    if (value === undefined || value === null) return fallback
    var text = String(value).trim()
    return text.length > 0 ? text : fallback
  }

  function flagToken(key, fallback) {
    var value = token(key, "").toLowerCase()
    if (value.length === 0) return fallback
    if (["1", "true", "yes", "on", "show", "shown", "visible"].indexOf(value) >= 0) return true
    if (["0", "false", "no", "off", "hide", "hidden"].indexOf(value) >= 0) return false
    return fallback
  }

  function numberToken(key, fallback) {
    var raw = token(key, "")
    if (raw.length === 0) return fallback
    var value = Number(raw)
    return isFinite(value) ? value : fallback
  }

  readonly property bool effectsEnabled: flagToken("effects", false)
  readonly property string primaryKind: token("effect-primary", "none")
  readonly property string secondaryKind: token("effect-secondary", "none")
  readonly property real effectIntensity: numberToken("effect-intensity", 1.0)
  readonly property real dualStrength: numberToken("effect-secondary-strength", 0.55)
  readonly property int effectVariant: Math.round(numberToken("effect-variant", 1))
  readonly property color effectTint: root.token("effect-tint", "").length > 0
    ? root.token("effect-tint", "#ffffff")
    : Color.accent
  readonly property color secondaryTint: root.token("effect-secondary-tint", "").length > 0
    ? root.token("effect-secondary-tint", "#ffffff")
    : root.effectTint

  // A wallpaper nobody can see is not worth animating. Windows on the focused
  // workspace mean the desktop is covered, and "pause" here means the shapes
  // stop being rendered at all rather than merely being hidden.
  readonly property bool desktopCovered: {
    if (!flagToken("pause-when-covered", true)) return false
    var ws = Hyprland.focusedWorkspace
    if (!ws || !ws.toplevels) return false
    return ws.toplevels.values.length > 0
  }

  // Battery policy: "never", "low" (under the threshold), or "always".
  readonly property string batteryPolicy: token("pause-on-battery", "low").toLowerCase()
  readonly property bool onBattery: {
    var device = UPower.displayDevice
    if (!device) return false
    return device.state === UPowerDeviceState.Discharging
  }
  readonly property real batteryLevel: {
    var device = UPower.displayDevice
    return device ? device.percentage * 100 : 100
  }
  readonly property bool batteryPaused: {
    if (!onBattery || batteryPolicy === "never") return false
    if (batteryPolicy === "always") return true
    return batteryLevel <= numberToken("pause-on-battery-below", 30)
  }

  readonly property bool effectsRunning:
    effectsEnabled && effectIntensity > 0 && !desktopCovered && !batteryPaused

  function imageUrl(path) {
    return Util.fileUrl(path)
  }

  function refreshBackground() {
    if (!readlinkProc.running) readlinkProc.running = true
  }

  function setBackground(path, instant) {
    transitionBackground("", path, path, instant, false)
  }

  function transitionBackground(fromPath, path, finalPath, instant, force) {
    path = String(path || "").trim()
    finalPath = String(finalPath || path).trim()
    fromPath = String(fromPath || "").trim()
    if (!path || (!force && finalPath === currentBackground)) return
    currentBackground = finalPath
    backgroundVersion += 1
    revealStartedVersion = -1

    revealAnimation.stop()
    finishingTransition = false

    if (instant || !displayedBackground) {
      oldBackground = ""
      incomingBackground = ""
      displayedBackground = path
      revealProgress = 1
      return
    }

    oldBackground = fromPath || displayedBackground
    incomingBackground = path
    revealProgress = 0
  }

  function setPendingTheme(colorsB64, shellB64) {
    pendingColorsRaw = Util.decodeBase64(colorsB64)
    pendingShellRaw = Util.decodeBase64(shellB64)
    pendingThemeVersion = backgroundVersion
    pendingThemeFallbackTimer.restart()
  }

  function applyPendingTheme() {
    // Background polling can advance backgroundVersion while a theme switch is
    // pending; the latest theme payload should still apply.
    if (pendingThemeVersion < 0) return
    pendingThemeFallbackTimer.stop()
    Color.loadColors(pendingColorsRaw)
    // Color.loadShell also refreshes Style so the type scale flips with the
    // background reveal instead of waiting for a separate reload path.
    Color.loadShell(pendingShellRaw)
    Style.scheduleRefresh()
    pendingThemeVersion = -1
    pendingColorsRaw = ""
    pendingShellRaw = ""
  }

  function transitionBackgroundWithTheme(fromPath, path, finalPath, colorsB64, shellB64) {
    transitionBackground(fromPath, path, finalPath, false, true)
    setPendingTheme(colorsB64, shellB64)
    if (!incomingBackground || revealProgress >= 1) applyPendingTheme()
  }

  function startReveal(panel) {
    if (!incomingBackground) return
    panel.maskReady = true
    if (revealStartedVersion === backgroundVersion) return
    revealStartedVersion = backgroundVersion
    applyPendingTheme()
    revealAnimation.restart()
  }

  function openSelector() {
    if (!bgSwitchProc.running) bgSwitchProc.running = true
  }

  function openThemeSwitcher() {
    if (!themeSwitchProc.running) themeSwitchProc.running = true
  }

  Process {
    id: bgSwitchProc
    command: ["bash", "-c", "background=$(omarchy-theme-bg-switcher); [[ -n $background ]] && omarchy-theme-bg-set \"$background\""]
    onExited: root.refreshBackground()
  }

  Process {
    id: themeSwitchProc
    command: ["bash", "-c", "theme=$(omarchy-theme-switcher); [[ -n $theme ]] && omarchy-theme-set \"$theme\" >/dev/null 2>&1 &"]
    onExited: root.refreshBackground()
  }

  Process {
    id: readlinkProc
    command: ["readlink", "-f", root.currentBackgroundLink]
    stdout: StdioCollector {
      onStreamFinished: root.setBackground(String(text || "").trim(), false)
    }
  }

  IpcHandler {
    target: "background"

    function refresh(): void {
      root.refreshBackground()
    }

    function set(path: string): void {
      root.setBackground(path, false)
    }

    function setInstant(path: string): void {
      root.setBackground(path, true)
    }

    function transition(fromPath: string, path: string): void {
      root.transitionBackground(fromPath, path, path, false, false)
    }

    function themeTransition(fromPath: string, path: string, finalPath: string, colorsB64: string, shellB64: string): void {
      root.transitionBackgroundWithTheme(fromPath, path, finalPath, colorsB64, shellB64)
    }
  }

  Timer {
    id: pendingThemeFallbackTimer
    interval: 300
    repeat: false
    onTriggered: root.applyPendingTheme()
  }

  NumberAnimation {
    id: revealAnimation
    target: root
    property: "revealProgress"
    from: 0
    to: 1
    duration: 420
    easing.type: Easing.InOutCubic
    onFinished: {
      if (root.incomingBackground) {
        root.displayedBackground = root.currentBackground || root.incomingBackground
        root.finishingTransition = true
      }
      root.revealProgress = 1
    }
  }

  // A background layer is awkward to introspect: it sits under every window and
  // has no visible chrome. `debug = "true"` under [background] logs the resolved
  // tokens and every gate transition to the shell journal, which is the quickest
  // way to answer "why is nothing moving".
  //   journalctl --user -f | grep ambient-bg
  function dbg(why) { if (!flagToken("debug", false)) return
    console.log("[ambient-bg] " + why
    + " enabled=" + effectsEnabled + " primary=" + primaryKind
    + " secondary=" + secondaryKind + " intensity=" + effectIntensity
    + " tint=" + effectTint + " covered=" + desktopCovered
    + " onBattery=" + onBattery + " level=" + Math.round(batteryLevel)
    + " batteryPaused=" + batteryPaused + " RUNNING=" + effectsRunning) }
  onEffectsRunningChanged: dbg("gate-changed")
  Component.onCompleted: { refreshBackground(); dbg("loaded") }

  Variants {
    model: Quickshell.screens

    PanelWindow {
      id: panel
      required property var modelData

      screen: modelData
      visible: !remapGuard.remapping
      anchors { top: true; bottom: true; left: true; right: true }

      ScreenMoveRemap {
        id: remapGuard
        window: panel
      }
      color: "transparent"
      // Keep render updates enabled. The background layer has been observed to
      // lose its committed buffer while parked with updatesEnabled=false,
      // leaving a black desktop until omarchy-shell is restarted. The wallpaper
      // itself is static, so this favors correctness over a small render-loop
      // optimization.
      updatesEnabled: true

      property bool maskReady: false

      function maybeStartReveal() {
        if (!root.incomingBackground || root.revealProgress !== 0 || maskReady) return
        if (incomingFrame.status !== Image.Ready) return
        Qt.callLater(function() {
          if (!root.incomingBackground || root.revealProgress !== 0 || maskReady) return
          if (incomingFrame.status !== Image.Ready) return
          root.startReveal(panel)
        })
      }

      WlrLayershell.namespace: "omarchy-background"
      WlrLayershell.layer: WlrLayer.Background
      WlrLayershell.keyboardFocus: WlrKeyboardFocus.None
      exclusionMode: ExclusionMode.Ignore

      Image {
        id: base
        anchors.fill: parent
        source: root.imageUrl(root.displayedBackground)
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: true
        onStatusChanged: {
          if (status === Image.Ready && root.finishingTransition) {
            root.incomingBackground = ""
            root.oldBackground = ""
            root.finishingTransition = false
          }
        }
      }

      Image {
        id: oldFrame
        anchors.fill: parent
        source: root.imageUrl(root.oldBackground)
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        cache: false
        smooth: true
        mipmap: true
        visible: root.oldBackground !== "" && root.revealProgress < 1
        onStatusChanged: panel.maybeStartReveal()
      }

      Item {
        id: incomingLayer
        anchors.fill: parent
        visible: root.incomingBackground !== "" && incomingFrame.status === Image.Ready && (root.revealProgress >= 1 || panel.maskReady)
        layer.enabled: root.incomingBackground !== "" && root.revealProgress < 1
        layer.smooth: true
        layer.effect: MultiEffect {
          maskEnabled: true
          maskSource: revealMask
          maskThresholdMin: 0.5
          maskSpreadAtMin: 0.02
        }

        Image {
          id: incomingFrame
          anchors.fill: parent
          source: root.imageUrl(root.incomingBackground)
          fillMode: Image.PreserveAspectCrop
          asynchronous: true
          cache: false
          smooth: true
          mipmap: true
          onStatusChanged: panel.maybeStartReveal()
        }
      }

      // Secondary type first, so the primary's motion sits in front of it.
      // Loader keeps the shapes out of the scene graph entirely while paused,
      // rather than animating them behind an opacity of zero.
      Loader {
        anchors.fill: parent
        active: root.effectsRunning && root.secondaryKind !== "none"
        sourceComponent: Ambient {
          kind: root.secondaryKind
          variant: root.effectVariant
          tint: root.secondaryTint
          intensity: root.effectIntensity * root.dualStrength
        }
      }

      Loader {
        anchors.fill: parent
        active: root.effectsRunning && root.primaryKind !== "none"
        sourceComponent: Ambient {
          kind: root.primaryKind
          variant: root.effectVariant
          tint: root.effectTint
          intensity: root.effectIntensity
        }
      }

      Item {
        id: revealMask
        anchors.fill: parent
        visible: false
        layer.enabled: true

        readonly property real slant: -0.18
        readonly property real centerTop: width / 2 - slant * height / 2
        readonly property real centerBottom: width / 2 + slant * height / 2
        readonly property real reach: width / 2 + Math.abs(slant) * height / 2 + 4
        readonly property real spread: reach * root.revealProgress

        Shape {
          anchors.fill: parent
          antialiasing: true
          preferredRendererType: Shape.CurveRenderer
          ShapePath {
            fillColor: "white"
            strokeColor: "transparent"
            startX: revealMask.centerTop - revealMask.spread; startY: 0
            PathLine { x: revealMask.centerTop + revealMask.spread; y: 0 }
            PathLine { x: revealMask.centerBottom + revealMask.spread; y: revealMask.height }
            PathLine { x: revealMask.centerBottom - revealMask.spread; y: revealMask.height }
            PathLine { x: revealMask.centerTop - revealMask.spread; y: 0 }
          }
        }
      }

      Connections {
        target: root
        function onIncomingBackgroundChanged() {
          panel.maskReady = false
          panel.maybeStartReveal()
        }
      }

      MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onDoubleClicked: function(mouse) {
          if (mouse.button === Qt.RightButton) root.openThemeSwitcher()
          else root.openSelector()
          mouse.accepted = true
        }
      }
    }
  }
}
