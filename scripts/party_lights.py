from rpi_ws281x import PixelStrip, Color
import time
import colorsys
import numpy as np

LED_COUNT = 150
LED_PIN = 21  # GPIO pin connected to the pixels
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10  # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False  # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0  # set to '1' for GPIOs 13, 19, 41, 45 or 53

NUM_STEPS = 50
CYCLE_LENGTH = 20  # seconds
BRIGHTNESS = 0.8
START_HUE = 270 / 360
STOP_HUE = 330 / 360


def change_color(strip, color):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()


def hsv_to_color(h, s, v):
    red, green, blue = colorsys.hsv_to_rgb(h=h, s=s, v=v)
    return Color(round(red * 255), round(green * 255), round(blue * 255))


if __name__ == "__main__":
    # Create NeoPixel object with appropriate configuration.
    strip = PixelStrip(
        LED_COUNT,
        LED_PIN,
        LED_FREQ_HZ,
        LED_DMA,
        LED_INVERT,
        LED_BRIGHTNESS,
        LED_CHANNEL,
    )
    # Intialize the library (must be called once before other functions).
    strip.begin()

    try:
        while True:
            for hue in np.linspace(start=START_HUE, stop=STOP_HUE, num=NUM_STEPS):
                change_color(strip, hsv_to_color(h=hue, s=1, v=BRIGHTNESS))
                time.sleep((CYCLE_LENGTH / 2) / NUM_STEPS)
            for hue in np.linspace(start=STOP_HUE, stop=START_HUE, num=NUM_STEPS):
                change_color(strip, hsv_to_color(h=hue, s=1, v=BRIGHTNESS))
                time.sleep((CYCLE_LENGTH / 2) / NUM_STEPS)
    except KeyboardInterrupt:
        pass
        # change_color(strip, Color(0, 0, 0))
