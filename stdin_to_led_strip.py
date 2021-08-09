import base64
import logging
from logzero import logger
import numpy as np
from rpi_ws281x import PixelStrip, Color
import scipy.fft
import sys

logger.setLevel(logging.INFO)


def clip(value, lower=0, upper=1):
    return lower if value < lower else upper if value > upper else value


class LedStripVisualizer:
    # LED strip configuration:
    LED_PIN = 21
    # LED_PIN = 10  # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
    LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
    LED_DMA = 10  # DMA channel to use for generating signal (try 10)
    LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
    LED_INVERT = (
        False  # True to invert the signal (when using NPN transistor level shift)
    )
    LED_CHANNEL = 0  # set to '1' for GPIOs 13, 19, 41, 45 or 53

    def __init__(self, led_count=10):
        super().__init__()
        # Create NeoPixel object with appropriate configuration.
        self.strip = PixelStrip(
            led_count,
            self.LED_PIN,
            self.LED_FREQ_HZ,
            self.LED_DMA,
            self.LED_INVERT,
            self.LED_BRIGHTNESS,
            self.LED_CHANNEL,
        )

        # Intialize the library (must be called once before other functions).
        self.strip.begin()

        logger.info("Strip intialized")

    def turn_off_leds(self):
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, Color(0, 0, 0))
        self.strip.show()

    def update(self, new_data):
        pass


class LedStripFrequencyVisualizer(LedStripVisualizer):
    FRAMERATE = 44100  # Number of frames per second
    FFT_SIZE = 44100 // 10  # Number of frames included in the FFT
    MAX_BRIGHTNESS_AMPLITUDE = 150000

    def __init__(self, led_count):
        super().__init__(led_count=led_count)
        self.signal = np.zeros(self.FFT_SIZE, dtype=np.int16)
        self.frequencies = scipy.fft.fftfreq(self.signal.size, 1 / self.FRAMERATE)

    def update(self, new_data):
        self.signal = np.concatenate((self.signal[len(new_data) :], new_data))
        amplitudes = abs(scipy.fft.fft(self.signal))
        self.update_leds(amplitudes / self.MAX_BRIGHTNESS_AMPLITUDE)

    def update_leds(self, normalized_amplitudes):
        brightness = int(255 * clip(np.average(normalized_amplitudes)))
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, Color(brightness, brightness, brightness))
        self.strip.show()


def main():
    visualizer = LedStripFrequencyVisualizer(led_count=10)

    try:
        for line in sys.stdin:
            logger.debug("new data")
            data = np.frombuffer(base64.b64decode(line), dtype="int16")

            visualizer.update(data)

    except KeyboardInterrupt:
        visualizer.turn_off_leds()


if __name__ == "__main__":
    main()
