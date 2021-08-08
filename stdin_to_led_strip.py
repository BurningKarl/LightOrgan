import colorsys
from rpi_ws281x import PixelStrip, Color

print("Libraries loaded")

# LED strip configuration:
LED_PIN = 21
# LED_PIN = 10  # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10  # DMA channel to use for generating signal (try 10)
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False  # True to invert the signal (when using NPN transistor level shift)
LED_CHANNEL = 0  # set to '1' for GPIOs 13, 19, 41, 45 or 53

START_OFFSET = 6
LEDS_PER_FREQUENCY_RANGE = 4
LEDS_BETWEEN_RANGES = 4
COLORS = [
    (2 / 3 + 0.025, 1.00, 1),  # Pure blue
    (0 / 3, 1.00, 1),  # Pure red
    (1 / 3 - 0.025, 1.00, 1),  # Pure green
]
COLOR_MODE = 2  # The index of HSV that is affected by incoming values

LED_COUNT = START_OFFSET + len(COLORS) * (
    LEDS_PER_FREQUENCY_RANGE + LEDS_BETWEEN_RANGES
)


def clip(value, lower=0, upper=1):
    return lower if value < lower else upper if value > upper else value


def turn_off(strip):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()


def update(brightness_values):
    for color_index, (base_color, value) in enumerate(zip(COLORS, brightness_values)):
        hsv_color = base_color[:COLOR_MODE] + (value,) + base_color[COLOR_MODE + 1 :]
        rgb_color = colorsys.hsv_to_rgb(*hsv_color)
        led_color = Color(*tuple(int(c * 255) for c in rgb_color))
        offset = START_OFFSET + color_index * (
            LEDS_PER_FREQUENCY_RANGE + LEDS_BETWEEN_RANGES
        )
        for i in range(LEDS_PER_FREQUENCY_RANGE):
            strip.setPixelColor(offset + i, led_color)
    strip.show()


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

    print("Strip intialized")

    try:
        # Ignore everything until '#'*10
        while True:
            input_string = input().strip()
            print("Setup:", input_string)
            if input_string == "#" * 10:
                break

        while True:
            input_string = input().strip()
            if not input_string:
                continue
            brightness_values = [clip(float(c)) for c in input_string.split(" ")]
            print(input_string)
            update(brightness_values)

    except KeyboardInterrupt:
        turn_off(strip)
