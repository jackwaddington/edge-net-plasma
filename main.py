"""edge-net LED display node (MicroPython / Pimoroni plasma) — dumb framebuffer.

Twin of the CircuitPython LED node: receives hex frames over MQTT and blits them.
No logic on the strip; senders decide what the pixels mean.

Subscribes:
  edge-net/gamepad/frame      -> hex, 6 chars/pixel RRGGBB -> blit
  edge-net/gamepad/led        -> "r,g,b" -> fill
  edge-net/gamepad/led/clear  -> off
"""
import time
import network
import plasma
from plasma import plasma_stick
from umqtt.simple import MQTTClient
import WIFI_CONFIG as W

NUM = 50
BRIGHT = 0.6
strip = plasma.WS2812(NUM, 0, 0, plasma_stick.DAT, color_order=plasma.COLOR_ORDER_RGB)
strip.start()


def _s(v):
    return int(v * BRIGHT)


def fill(r, g, b):
    for i in range(NUM):
        strip.set_rgb(i, _s(r), _s(g), _s(b))


def on_msg(topic, msg):
    t = topic.decode()
    if t.endswith("/frame"):
        m = msg.decode()
        n = min(NUM, len(m) // 6)
        for i in range(n):
            j = i * 6
            try:
                strip.set_rgb(i, _s(int(m[j:j + 2], 16)),
                              _s(int(m[j + 2:j + 4], 16)),
                              _s(int(m[j + 4:j + 6], 16)))
            except ValueError:
                pass
    elif t.endswith("/clear"):
        fill(0, 0, 0)
    else:
        try:
            r, g, b = (int(v) for v in msg.decode().split(","))
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
print("wifi ok", wlan.ifconfig()[0])
fill(0, 40, 80)  # idle teal

BROKER = "10.1.1.1"
DEVICE_ID = "2"   # also answer on our own channel, for individual control
TOPICS = (
    b"edge-net/gamepad/frame", b"edge-net/gamepad/led", b"edge-net/gamepad/led/clear",
    ("edge-net/plasma/%s/frame" % DEVICE_ID).encode(),
    ("edge-net/plasma/%s/led" % DEVICE_ID).encode(),
    ("edge-net/plasma/%s/led/clear" % DEVICE_ID).encode(),
)
mqtt = MQTTClient("edge-net-led2", BROKER, port=1883, keepalive=60)
mqtt.set_callback(on_msg)
mqtt.connect()
for t in TOPICS:
    mqtt.subscribe(t)
print("LED node ready ->", BROKER)

last_ping = time.ticks_ms()
while True:
    try:
        mqtt.check_msg()
    except OSError:
        try:
            mqtt.connect()
            for t in TOPICS:
                mqtt.subscribe(t)
        except Exception:
            time.sleep(1)
    if time.ticks_diff(time.ticks_ms(), last_ping) > 15000:
        try:
            mqtt.ping()
        except Exception:
            pass
        last_ping = time.ticks_ms()
