#!/usr/bin/env python3
# NeoPixel library strandtest example
# Author: Tony DiCola (tony@tonydicola.com)
#
# Direct port of the Arduino NeoPixel library strandtest example.  Showcases
# various animations on a strip of NeoPixels.

import time
import sys
import colorsys
from rpi_ws281x import PixelStrip, Color

print('Libraries loaded')

# LED strip configuration:
LED_PIN = 21
# LED_PIN = 10        # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53

LEDS_PER_FREQUENCY_RANGE = 3
LEDS_BETWEEN_RANGES = 1
COLORS = [
    (2/3, 1, 1), # Pure blue
    (0/3, 1, 1), # Pure red
    (1/3, 1, 1), # Pure green
]

LED_COUNT = len(COLORS) * (LEDS_PER_FREQUENCY_RANGE + LEDS_BETWEEN_RANGES)

def clip(value, lower=0, upper=1):
    return lower if value < lower else upper if value > upper else value

def colorWipe(strip, color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms / 1000.0)

def update(brightness_values):
    for color_index, (base_color, value) in enumerate(zip(COLORS, brightness_values)):
        rgb_color = colorsys.hsv_to_rgb(base_color[0], base_color[1], value)
        led_color = Color(*tuple(int(c*255) for c in rgb_color))
        offset = color_index * (LEDS_PER_FREQUENCY_RANGE + LEDS_BETWEEN_RANGES)
        for i in range(LEDS_PER_FREQUENCY_RANGE):
            strip.setPixelColor(offset + i, led_color)
    strip.show()

if __name__ == '__main__':
    # Create NeoPixel object with appropriate configuration.
    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    # Intialize the library (must be called once before other functions).
    strip.begin()

    print('Strip intialized')

    try:
        # Ignore everything until '#'*10
        while True:
            input_string = input().strip()
            print('Setup:', input_string)
            if input_string == '#'*10:
                break

        while True:
            input_string = input().strip()
            if not input_string:
                continue
            brightness_values = [clip(float(c)) for c in input_string.split(' ')]
            print(brightness_values)
            update(brightness_values)

    except KeyboardInterrupt:
        colorWipe(strip, Color(0, 0, 0), 10)
