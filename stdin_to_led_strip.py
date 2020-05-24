#!/usr/bin/env python3
# NeoPixel library strandtest example
# Author: Tony DiCola (tony@tonydicola.com)
#
# Direct port of the Arduino NeoPixel library strandtest example.  Showcases
# various animations on a strip of NeoPixels.

import time
import sys
from rpi_ws281x import PixelStrip, Color

print('Libraries loaded')

# LED strip configuration:
LED_COUNT = 9
LED_PIN = 21
# LED_PIN = 10        # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10          # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0       # set to '1' for GPIOs 13, 19, 41, 45 or 53


# Define functions which animate LEDs in various ways.
def colorWipe(strip, color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms / 1000.0)

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
            print('Pre:', input_string)
            if input_string == '#'*10:
                break

        while True:
            input_string = input().strip()
            if not input_string:
                continue
            brightnesses = [min(max(0, int(c)), 255) for c in input_string.split(' ')]
            print(input_string, brightnesses)
            # Low range: blue
            strip.setPixelColor(0, Color(0, 0, brightnesses[0]))
            strip.setPixelColor(1, Color(0, 0, brightnesses[0]))
            # Mid range: red
            strip.setPixelColor(3, Color(brightnesses[1], 0, 0))
            strip.setPixelColor(4, Color(brightnesses[1], 0, 0))
            # High range: green
            strip.setPixelColor(6, Color(0, brightnesses[2], 0))
            strip.setPixelColor(7, Color(0, brightnesses[2], 0))
            strip.show()

    except KeyboardInterrupt:
        colorWipe(strip, Color(0, 0, 0), 10)
