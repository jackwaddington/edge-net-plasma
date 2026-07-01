"""edge-net LED display node (MicroPython / Pimoroni plasma) — framebuffer + animations.

Three modes:
  frame   — raw per-pixel hex, blits immediately (chess clock, gamepad, reactive)
  animate — named onboard animation, runs until next command
  fill    — solid colour, instant

Subscribes (shared):
  edge-net/gamepad/frame        -> hex string, 6 chars/pixel RRGGBB
  edge-net/gamepad/led          -> "r,g,b" solid fill
  edge-net/gamepad/led/clear    -> off
  edge-net/gamepad/animate      -> animation command (see below)

Subscribes (this device only, DEVICE_ID = "2"):
  edge-net/plasma/2/frame
  edge-net/plasma/2/led
  edge-net/plasma/2/led/clear
  edge-net/plasma/2/animate

Subscribes (MCP command interface):
  edge-net/plasma/cmd           -> JSON {"action":"set_led_pattern","pattern":"...","color":"#rrggbb","correlationId":"..."}

Publishes:
  edge-net/plasma/state  (retain=True)  -> JSON {"pattern":"...","color":"..."}
  edge-net/plasma/ack                   -> JSON {"correlationId":"...","ok":true}

Animation commands (via /animate or MCP pattern field):
  rainbow [speed]               -> walking rainbow, optional speed 1-255 (default 20)
  fade <HEX,HEX,...>            -> smooth fade loop between colours e.g. FF0000,0000FF,FF6600
  flash <HEX,HEX,...>           -> hard flash between colours
  fire                          -> fire effect
  off                           -> stop animation, clear strip
  stop                          -> same as off

A /frame message always interrupts the current animation (one-shot blit).
A /animate or /led command replaces the current animation.
"""
import time
import network
import plasma
import ujson
from umqtt.simple import MQTTClient
import WIFI_CONFIG as W
from random import random, uniform

NUM = 50
BRIGHT = 0.6
DAT = 15  # Plasma Stick 2040W data pin
strip = plasma.WS2812(NUM, 0, 0, DAT, color_order=plasma.COLOR_ORDER_RGB)
strip.start()

# Animation state
_anim = None        # None = idle, string = current animation name
_anim_args = []     # parsed animation arguments
_anim_offset = 0.0  # shared offset/counter for animations
_state_color = None # last solid colour set via MCP (hex string, e.g. "FF0000")

# MCP topics
TOPIC_CMD   = b"edge-net/plasma/cmd"
TOPIC_STATE = b"edge-net/plasma/state"
TOPIC_ACK   = b"edge-net/plasma/ack"


def _s(v):
    return int(v * BRIGHT)


def fill(r, g, b):
    for i in range(NUM):
        strip.set_rgb(i, _s(r), _s(g), _s(b))


def _parse_colours(arg):
    """'FF0000,0000FF,FF6600' -> [(255,0,0), (0,0,255), (255,102,0)]"""
    out = []
    for h in arg.split(","):
        h = h.strip()
        if len(h) == 6:
            try:
                out.append((int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)))
            except ValueError:
                pass
    return out


def _lerp(a, b, t):
    return int(a + (b - a) * t)


def _hex_to_rgb(h):
    """'#FF00AA' or 'FF00AA' -> (255, 0, 170), or None on failure."""
    h = h.lstrip("#")
    if len(h) != 6:
        return None
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except ValueError:
        return None


def _publish_state():
    state = ujson.dumps({"pattern": _anim or "off", "color": _state_color})
    try:
        mqtt.publish(TOPIC_STATE, state.encode(), retain=True, qos=1)
    except Exception:
        pass


def _handle_cmd(payload):
    """Handle a JSON command from edge-net/plasma/cmd."""
    global _anim, _anim_args, _anim_offset, _state_color
    try:
        cmd = ujson.loads(payload)
    except Exception:
        return
    action = cmd.get("action", "")
    correlation_id = cmd.get("correlationId", "")

    if action == "set_led_pattern":
        pattern = cmd.get("pattern", "off").lower()
        color_hex = (cmd.get("color") or "").lstrip("#").upper() or None

        if pattern == "solid":
            rgb = _hex_to_rgb(color_hex) if color_hex else (255, 255, 255)
            if rgb:
                _anim = "off"
                _anim_args = []
                _anim_offset = 0.0
                _state_color = color_hex
                fill(rgb[0], rgb[1], rgb[2])
        elif pattern == "pulse":
            hex_arg = (color_hex or "FFFFFF") + ",000000"
            _anim = "fade"
            _anim_args = [hex_arg]
            _anim_offset = 0.0
            _state_color = color_hex
        elif pattern in ("rainbow", "fire", "fade", "flash"):
            _anim = pattern
            _anim_args = []
            _anim_offset = 0.0
            _state_color = color_hex
        elif pattern in ("off", "stop"):
            _anim = "off"
            _anim_args = []
            _anim_offset = 0.0
            _state_color = None
            fill(0, 0, 0)

    _publish_state()
    if correlation_id:
        try:
            mqtt.publish(TOPIC_ACK, ujson.dumps({"correlationId": correlation_id, "ok": True}).encode(), qos=1)
        except Exception:
            pass


def _set_anim(cmd):
    global _anim, _anim_args, _anim_offset
    parts = cmd.strip().split()
    name = parts[0].lower() if parts else "off"
    args = parts[1:] if len(parts) > 1 else []
    _anim = name
    _anim_args = args
    _anim_offset = 0.0


def _step_animation():
    """Run one animation frame. Returns suggested sleep in seconds."""
    global _anim_offset

    if _anim is None or _anim in ("off", "stop"):
        return 0.1

    if _anim == "rainbow":
        speed = int(_anim_args[0]) if _anim_args else 20
        _anim_offset = (_anim_offset + speed / 2000.0) % 1.0
        for i in range(NUM):
            strip.set_hsv(i, (i / NUM + _anim_offset) % 1.0, 1.0, BRIGHT)
        return 1.0 / 60

    if _anim == "fire":
        for i in range(NUM):
            strip.set_hsv(i, uniform(0.0, 0.06), 1.0, random() * BRIGHT)
        return 0.05

    if _anim == "fade":
        colours = _parse_colours(_anim_args[0]) if _anim_args else [(255, 0, 0), (0, 0, 255)]
        if len(colours) < 2:
            return 0.1
        n = len(colours)
        cycle = 4.0                          # seconds per full loop
        t = (_anim_offset % cycle) / cycle * n
        idx = int(t) % n
        frac = t - int(t)
        a = colours[idx]
        b = colours[(idx + 1) % n]
        r = _lerp(a[0], b[0], frac)
        g = _lerp(a[1], b[1], frac)
        b_ = _lerp(a[2], b[2], frac)
        fill(r, g, b_)
        _anim_offset += 0.05
        return 0.05

    if _anim == "flash":
        colours = _parse_colours(_anim_args[0]) if _anim_args else [(255, 0, 0), (0, 0, 255)]
        if not colours:
            return 0.1
        idx = int(_anim_offset) % len(colours)
        c = colours[idx]
        fill(c[0], c[1], c[2])
        _anim_offset += 1
        return 0.4

    return 0.1


def on_msg(topic, msg):
    global _anim
    t = topic.decode()
    m = msg.decode().strip()

    if t == "edge-net/plasma/cmd":
        _handle_cmd(m)
        return

    if t.endswith("/frame"):
        # Raw frame — blit immediately; does NOT clear animation state
        n = min(NUM, len(m) // 6)
        for i in range(n):
            j = i * 6
            try:
                strip.set_rgb(i, _s(int(m[j:j + 2], 16)),
                              _s(int(m[j + 2:j + 4], 16)),
                              _s(int(m[j + 4:j + 6], 16)))
            except ValueError:
                pass

    elif t.endswith("/animate"):
        _set_anim(m)
        if m.lower() in ("off", "stop"):
            fill(0, 0, 0)

    elif t.endswith("/clear"):
        _anim = "off"
        fill(0, 0, 0)

    else:
        # /led — solid fill, stops animation
        try:
            r, g, b = (int(v) for v in m.split(","))
            _anim = "off"
            fill(r, g, b)
        except ValueError:
            pass


try:
    import rp2
    rp2.country(W.COUNTRY)
except Exception:
    pass

fill(20, 0, 0)   # red = connecting
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(W.SSID, W.PSK)
t0 = time.time()
while not wlan.isconnected():
    if time.time() - t0 > 25:
        fill(40, 0, 0)
        raise RuntimeError("wifi connect failed")
    time.sleep(0.3)
_ip = wlan.ifconfig()[0]
print("wifi ok", _ip)
fill(0, 40, 80)  # idle teal

try:
    import webrepl
    webrepl.start(password="edge-net")
except ImportError:
    pass

BROKER = "10.1.1.1"
DEVICE_ID = "2"
TOPICS = (
    b"edge-net/gamepad/frame", b"edge-net/gamepad/led", b"edge-net/gamepad/led/clear",
    b"edge-net/gamepad/animate",
    ("edge-net/plasma/%s/frame" % DEVICE_ID).encode(),
    ("edge-net/plasma/%s/led" % DEVICE_ID).encode(),
    ("edge-net/plasma/%s/led/clear" % DEVICE_ID).encode(),
    ("edge-net/plasma/%s/animate" % DEVICE_ID).encode(),
)
NODE_NAME = "plasma-%s" % DEVICE_ID
TOPIC_STATUS = ("edge-net/%s/status" % NODE_NAME).encode()
STATUS_ONLINE  = ('{"status":"online","ip":"%s","fw":"%s"}' % (_ip, NODE_NAME)).encode()
STATUS_OFFLINE = b'{"status":"offline"}'

mqtt = MQTTClient("edge-net-%s" % NODE_NAME, BROKER, port=1883, keepalive=60)
mqtt.set_last_will(TOPIC_STATUS, STATUS_OFFLINE, retain=True, qos=1)
mqtt.set_callback(on_msg)
mqtt.connect()
mqtt.publish(TOPIC_STATUS, STATUS_ONLINE, retain=True, qos=1)
for t in TOPICS:
    mqtt.subscribe(t)
mqtt.subscribe(TOPIC_CMD)
_publish_state()
print("%s ready -> %s" % (NODE_NAME, BROKER))

last_ping = time.ticks_ms()
while True:
    try:
        mqtt.check_msg()
    except OSError:
        try:
            mqtt.connect()
            mqtt.publish(TOPIC_STATUS, STATUS_ONLINE, retain=True, qos=1)
            for t in TOPICS:
                mqtt.subscribe(t)
            mqtt.subscribe(TOPIC_CMD)
            _publish_state()
        except Exception:
            time.sleep(1)

    sleep_ms = int(_step_animation() * 1000)

    if time.ticks_diff(time.ticks_ms(), last_ping) > 15000:
        try:
            mqtt.ping()
        except Exception:
            pass
        last_ping = time.ticks_ms()

    time.sleep_ms(max(10, sleep_ms))
