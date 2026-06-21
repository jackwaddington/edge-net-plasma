import plasma
from plasma import plasma_stick
import time
from random import random, uniform

"""
A basic fire effect.
"""

# Set how many LEDs you have
NUM_LEDS = 50

# WS2812 / NeoPixel™ LEDs
led_strip = plasma.WS2812(NUM_LEDS, 0, 0, plasma_stick.DAT, color_order=plasma.COLOR_ORDER_RGB)

# Start updating the LED strip
led_strip.start()

while True:
    # fire effect! Random red/orange hue, full saturation, random brightness
    for i in range(NUM_LEDS):
        led_strip.set_hsv(i, uniform(1.0, 100 / 200), 1.0, random())
    time.sleep(0.3)