import base64
import colorsys
import easing_functions
import logging
from logzero import logger
import numpy as np
from rpi_ws281x import PixelStrip, Color
import scipy.fft
import sys
import time

logger.setLevel(logging.INFO)


def clip(value, lower=0, upper=1):
    return lower if value < lower else upper if value > upper else value


class Visualizer:
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
        self.led_count = led_count

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


class FrequencyVisualizer(Visualizer):
    FRAMERATE = 44100  # Number of frames per second
    FFT_SIZE = 44100 // 10  # Number of frames included in the FFT
    MAX_BRIGHTNESS_AMPLITUDE = 3_000_000

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


class FrequencyBandsVisualizer(FrequencyVisualizer):
    COLORS = [
        (2 / 3 + 0.025, 1.00, 1),  # Pure blue
        (0 / 3, 1.00, 1),  # Pure red
        (1 / 3 - 0.025, 1.00, 1),  # Pure green
    ]

    def __init__(self, leds_per_band=4):
        led_count = leds_per_band * 3
        super().__init__(led_count=led_count)
        self.leds_per_band = leds_per_band

        # Human hearing range: 20Hz to 20,000Hz
        # Frequency table
        # Name            Range (in Hz)  Use
        # Sub-bass        20 - 60        Felt, sense of power
        # Bass            60 - 250       Fundamental notes
        # Low midrange    250 - 500      Bass instruments
        # Midrange        500 - 2000     Instruments & vocals
        # Upper midrange  2000 - 4000    Percussion & vocals
        # Presence        4000 - 6000    Clarity & defintion
        # Brilliance      6000 - 20000   Sparkle
        self.band_masks = [
            (250 < self.frequencies) & (self.frequencies <= 500),
            (500 < self.frequencies) & (self.frequencies <= 2000),
            (2000 < self.frequencies) & (self.frequencies <= 4000),
        ]
        self.band_sizes = [np.sum(mask) for mask in self.band_masks]

    def update_leds(self, normalized_amplitudes):
        brightness_values = [
            clip(np.sum(normalized_amplitudes[mask]) / size)
            for mask, size in zip(self.band_masks, self.band_sizes)
        ]

        for color_index, (base_color, value) in enumerate(
            zip(self.COLORS, brightness_values)
        ):
            hsv_color = base_color[:2] + (value,)
            rgb_color = colorsys.hsv_to_rgb(*hsv_color)
            led_color = Color(*tuple(round(c * 255) for c in rgb_color))
            offset = color_index * self.leds_per_band
            for i in range(self.leds_per_band):
                self.strip.setPixelColor(offset + i, led_color)
        self.strip.show()


class FrequencyWaveVisualizer(FrequencyVisualizer):
    def __init__(
        self,
        led_count=10,
        cycle_hues=False,
        easing_factory=easing_functions.LinearInOut,
    ):
        super().__init__(led_count=led_count)
        self.hues = np.linspace(0, 1, num=self.led_count, endpoint=False)
        self.frequency_cutoffs = np.logspace(
            np.log10(60),
            np.log10(2000),
            num=self.led_count + 1,
        )
        logger.info(f"frequency_cutoffs={self.frequency_cutoffs}")
        self.bin_masks = [
            (self.frequency_cutoffs[i] < self.frequencies)
            & (self.frequencies <= self.frequency_cutoffs[i + 1])
            for i in range(self.led_count)
        ]
        self.bin_sizes = [np.sum(mask) for mask in self.bin_masks]
        logger.info(f"bin_sizes={self.bin_sizes}")

        self.cycle_hues = cycle_hues
        self.last_hue_update = time.monotonic()

        self.easing_function = easing_factory(start=0, end=1, duration=1)

    def update_leds(self, normalized_amplitudes):
        if self.cycle_hues and int(time.monotonic() * 10) > int(
            self.last_hue_update * 10
        ):
            self.hues = np.roll(self.hues, 1)
            logger.debug(f"hues: {self.hues!r}")
            self.last_hue_update = time.monotonic()

        brightness_values = [
            clip(np.sum(normalized_amplitudes[mask]) / size)
            for mask, size in zip(self.bin_masks, self.bin_sizes)
        ]
        brightness_values = [self.easing_function(v) for v in brightness_values]
        logger.debug(
            "brightness_values: "
            + (", ".join([f"{val:0.03f}" for val in brightness_values]))
        )

        for i, (hue, brightness) in enumerate(zip(self.hues, brightness_values)):
            rgb_color = colorsys.hsv_to_rgb(hue, 1, brightness)
            led_color = Color(*tuple(round(c * 255) for c in rgb_color))
            self.strip.setPixelColor(i, led_color)
        self.strip.show()


def main():
    visualizer = FrequencyWaveVisualizer(
        led_count=16, easing_factory=easing_functions.CubicEaseIn
    )

    try:
        for line in sys.stdin:
            data = np.frombuffer(base64.b64decode(line), dtype="int16")
            visualizer.update(data)

    except KeyboardInterrupt:
        visualizer.turn_off_leds()


if __name__ == "__main__":
    main()
