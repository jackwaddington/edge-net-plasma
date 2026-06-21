# edge-net-plasma

A node in [Edge-NET](https://github.com/jackwaddington/edge-net). A Pimoroni
Plasma Stick 2040W (CircuitPython) driving a 50-LED WS2812 strip as a **dumb
framebuffer display**: it receives pixel frames over MQTT and blits them. All the
cleverness — text rendering, animation, the 5×10 matrix mapping — lives *off*
this device, on the sender. So this firmware is tiny and never needs to change.

## Hardware

- [Pimoroni Plasma Stick 2040W](https://shop.pimoroni.com/products/plasma-stick-2040-w) (RP2040 + WiFi, CircuitPython)
- WS2812 / NeoPixel strip — 50 LEDs on `GP15`

## Role — dumb strip, smart edge

The strip shows whatever frame it's sent; the sender decides what the pixels
*mean*. This is the level-2 "declarative" pattern from the edge repo's
`docs/PLANNING.md`. Because this node does nothing but receive-and-show in a
tight loop (no buttons, no joystick — input lives on the gamepad/GFX), playback
is smooth enough for streamed animation.

This stick used to be the gamepad host; the GamepadQT moved to the GFX, freeing
this one to be a dedicated display.

## MQTT topics (subscribe)

| Topic | Payload | Effect |
| ----- | ------- | ------ |
| `edge-net/gamepad/frame` | hex string, 6 chars/pixel `RRGGBB` (300 chars for 50 px) | blit the frame |
| `edge-net/gamepad/led` | `r,g,b` | fill solid |
| `edge-net/gamepad/led/clear` | — | off |

Topics keep the `gamepad/` prefix for now so the existing rule + senders work
unchanged — rename to `plasma/` later if desired.

## Sender

[`sender/textmatrix.py`](sender/textmatrix.py) renders a word into scrolling
frames for a **10×5 serpentine matrix** (3×5 font) and prints one hex frame per
line. Stream them to the broker from a host on the AP (the hub has no python3,
so render elsewhere and pipe):

```bash
python3 sender/textmatrix.py "HELLO" > frames.txt
# then, on a host that can reach 10.1.1.1 (e.g. the hub):
while IFS= read -r f; do echo "$f"; sleep 0.05; done < frames.txt \
  | mosquitto_pub -h 10.1.1.1 -t edge-net/gamepad/frame -l   # one persistent connection = smooth
```

## Software

CircuitPython. Flash via USB: copy `code.py` + a filled-in `config.py` (from
`config.example.py`) to `CIRCUITPY`. Needs `adafruit_minimqtt` in `lib/`
(`circup install adafruit_minimqtt`). WiFi secret stays out of git.

## Status / next

- ✅ Per-pixel addressing + **smooth** framebuffer playback.
- ✅ Text renderer (5×10 serpentine, 3×5 font).
- ⬜ Physically fold the strip into 5 rows of 10 (serpentine), then verify/adjust
  `xy_to_index` if letters come out mirrored/flipped.
- ⬜ Ambient mode (idle weather/glow, interrupt on frames) — see [PLAN.md](PLAN.md).

## Part of Edge-NET

See [Edge-NET](https://github.com/jackwaddington/edge-net).
