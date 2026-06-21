# edge-net-plasma — parked plan (weather stick)

**Status: parked.** This Plasma Stick is physically hard to access (mounted in
place; would have to be taken down, plugged in, flashed, tested). Strong
candidate to receive an OTA updater agent so it only needs one more physical
flash ever. See `docs/PLANNING.md → Software Deployment` in the edge-net repo.

## What this node should become

The **ambient + interrupt** pattern for an output node:

- **Default (ambient):** shows weather, as it does today.
- **Listens** on MQTT for commands while ambient runs.
- **On command:** drop weather, do the commanded thing.
- **Fallback:** ~30s with no new command → drift back to weather automatically.

It subscribes to the gamepad's topics directly and decides for itself what to
do — matches the Edge-NET principle: the gamepad publishes intent, any node
reacts. (See edge-net-gamepad.)

## First tracer bullet (when we pick this back up)

Press a gamepad button → weather stick interrupts weather, flashes a solid
colour, returns to weather after 30s idle.

Button → colour map (mirrors the gamepad's local strip):

| Button | Effect |
| ------ | ------ |
| A | red |
| B | green |
| X | blue |
| Y | rainbow |

Subscribe: `edge-net/gamepad/button/#` (payloads `press` / `release`).

## MUST DO FIRST — capture the existing weather code

The current weather firmware exists **only on the physical device**, not in this
repo (repo has README + this file only). Before changing anything: plug in,
read the running code off the device, and commit it here as the baseline.
Otherwise an edit could lose the only copy.

## Config to update on flash

- WiFi SSID `Pirie`, password in edge-net-secrets (`andSon60`)
- MQTT broker `10.1.1.1:1883`
- This board runs **MicroPython** (per README) — OTA path is `umqtt` →
  `open('main.py','w')` → `machine.reset()`, cleaner than CircuitPython's
  USB-mass-storage filesystem conflict.

## Open question

Whether to flash the ambient+interrupt firmware and the OTA agent in the **same**
physical visit (recommended — one trip), having first proven the OTA loop on the
easier-to-reach GFX / Inky nodes.
