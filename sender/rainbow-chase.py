"""Walking rainbow sender — streams frames to edge-net/gamepad/frame via MQTT.

Each frame shifts the hue offset by one step, producing a smooth chase effect.
Runs until Ctrl-C.

Usage:
    python3 sender/rainbow-chase.py [--fps 30] [--host 10.1.1.1]
"""
import argparse
import time
import paho.mqtt.client as mqtt

NUM = 50
TOPIC = "edge-net/gamepad/frame"


def hue_to_rgb(h):
    """h in [0,1) -> (r,g,b) each 0-255."""
    h6 = h * 6
    x = h6 - int(h6)
    i = int(h6) % 6
    if i == 0: return (255, int(255 * x), 0)
    if i == 1: return (int(255 * (1 - x)), 255, 0)
    if i == 2: return (0, 255, int(255 * x))
    if i == 3: return (0, int(255 * (1 - x)), 255)
    if i == 4: return (int(255 * x), 0, 255)
    return (255, 0, int(255 * (1 - x)))


def rainbow_frame(offset):
    buf = []
    for i in range(NUM):
        r, g, b = hue_to_rgb((i / NUM + offset) % 1.0)
        buf.append("%02X%02X%02X" % (r, g, b))
    return "".join(buf)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fps", type=float, default=30)
    p.add_argument("--host", default="10.1.1.1")
    p.add_argument("--port", type=int, default=1883)
    args = p.parse_args()

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(args.host, args.port)
    client.loop_start()

    interval = 1.0 / args.fps
    step = 1.0 / NUM       # shift one pixel-width per frame
    offset = 0.0
    print(f"Sending rainbow chase to {args.host}:{args.port} @ {args.fps:.0f} fps — Ctrl-C to stop")
    try:
        while True:
            t0 = time.monotonic()
            client.publish(TOPIC, rainbow_frame(offset))
            offset = (offset + step) % 1.0
            elapsed = time.monotonic() - t0
            sleep = interval - elapsed
            if sleep > 0:
                time.sleep(sleep)
    except KeyboardInterrupt:
        pass
    finally:
        client.publish(TOPIC, "000000" * NUM)   # clear on exit
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
