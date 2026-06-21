"""edge-net LED display node — Plasma Stick 2040W, dedicated framebuffer.

Does ONE thing: receive frames over MQTT and blit them, in a tight loop, so
animation plays smoothly. No buttons, no joystick (that moves to the GFX). The
stick stays dumb — the sender decides what the pixels mean.

Subscribes:
  edge-net/gamepad/frame  -> hex string, 6 chars/pixel (RRGGBB) -> blit
  edge-net/gamepad/led    -> "r,g,b" -> fill
  edge-net/gamepad/led/clear -> off
"""

import time
import board
import neopixel
import wifi
import socketpool
import adafruit_minimqtt.adafruit_minimqtt as MQTT

import config

NUM = config.NUM_LEDS
pixels = neopixel.NeoPixel(
    getattr(board, config.LED_PIN), NUM, auto_write=False
)
pixels.brightness = 0.6
pixels.fill((0, 0, 0))
pixels.show()


def on_msg(client, topic, message):
    if topic.endswith("/frame"):
        n = min(NUM, len(message) // 6)
        for i in range(n):
            j = i * 6
            try:
                pixels[i] = (int(message[j:j + 2], 16),
                             int(message[j + 2:j + 4], 16),
                             int(message[j + 4:j + 6], 16))
            except ValueError:
                pass
        pixels.show()
    elif topic.endswith("/clear"):
        pixels.fill((0, 0, 0))
        pixels.show()
    else:
        try:
            r, g, b = (int(v) for v in message.split(","))
            pixels.fill((r, g, b))
            pixels.show()
        except ValueError:
            pass


wifi.radio.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
pool = socketpool.SocketPool(wifi.radio)
mqtt = MQTT.MQTT(
    broker=config.MQTT_BROKER,
    port=config.MQTT_PORT,
    client_id="edge-net-led",
    socket_pool=pool,
    socket_timeout=1,
    keep_alive=60,
)
mqtt.on_message = on_msg
mqtt.connect()
mqtt._socket_timeout = 0.02          # tight servicing for smooth frame playback
mqtt.subscribe("edge-net/gamepad/frame")
mqtt.subscribe("edge-net/gamepad/led")
mqtt.subscribe("edge-net/gamepad/led/clear")
print("LED node ready ->", wifi.radio.ipv4_address)

# A gentle "I'm online" idle glow until the first frame arrives.
pixels.fill((0, 40, 80))
pixels.show()

last_ping = time.monotonic()
while True:
    try:
        mqtt.loop(timeout=0.02)
    except Exception:
        pass
    now = time.monotonic()
    if now - last_ping > 20:
        try:
            mqtt.ping()
        except Exception:
            pass
        last_ping = now
