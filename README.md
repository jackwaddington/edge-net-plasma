# edge-net-plasma

A node in [Edge-NET](https://github.com/jackwaddington/edge-net). A Pimoroni Plasma Stick 2040W running MicroPython, connected to the edge-net WiFi and subscribed to MQTT topics. Drives an LED strip, changing patterns in response to messages from other nodes — particularly the Keybow.

## Hardware

- [Pimoroni Plasma Stick 2040W](https://shop.pimoroni.com/products/plasma-stick-2040-w)
- LED strip (WS2812 / NeoPixel compatible)

## What it does

- Connects to the Edge-NET WiFi network
- Connects to the Mosquitto MQTT broker on the hub
- Subscribes to topics published by the Keybow (and potentially other nodes)
- Changes LED pattern, colour, or brightness based on received messages

## Software

MicroPython. The Plasma Stick must be flashed via USB to update.

## MQTT topics

| Topic | Direction | Description |
| ----- | --------- | ----------- |
| TBD | subscribe | LED pattern / colour commands |

## Part of Edge-NET

See [Edge-NET](https://github.com/jackwaddington/edge-net) for the full architecture and list of nodes.
