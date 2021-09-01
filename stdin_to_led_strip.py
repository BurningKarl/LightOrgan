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


# Taken from https://matplotlib.org/stable/_modules/matplotlib/colors.html#hsv_to_rgb
def hsv_to_rgb(hsv):
    """
    Convert hsv values to rgb.

    Parameters
    ----------
    hsv : (..., 3) array-like
       All values assumed to be in range [0, 1]

    Returns
    -------
    (..., 3) ndarray
       Colors converted to RGB values in range [0, 1]
    """
    hsv = np.asarray(hsv)

    # check length of the last dimension, should be _some_ sort of rgb
    if hsv.shape[-1] != 3:
        raise ValueError(
            "Last dimension of input array must be 3; "
            "shape {shp} was found.".format(shp=hsv.shape)
        )

    in_shape = hsv.shape
    hsv = np.array(
        hsv,
        copy=False,
        dtype=np.promote_types(hsv.dtype, np.float32),  # Don't work on ints.
        ndmin=2,  # In case input was 1D.
    )

    h = hsv[..., 0]
    s = hsv[..., 1]
    v = hsv[..., 2]

    r = np.empty_like(h)
    g = np.empty_like(h)
    b = np.empty_like(h)

    i = (h * 6.0).astype(int)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))

    idx = i % 6 == 0
    r[idx] = v[idx]
    g[idx] = t[idx]
    b[idx] = p[idx]

    idx = i == 1
    r[idx] = q[idx]
    g[idx] = v[idx]
    b[idx] = p[idx]

    idx = i == 2
    r[idx] = p[idx]
    g[idx] = v[idx]
    b[idx] = t[idx]

    idx = i == 3
    r[idx] = p[idx]
    g[idx] = q[idx]
    b[idx] = v[idx]

    idx = i == 4
    r[idx] = t[idx]
    g[idx] = p[idx]
    b[idx] = v[idx]

    idx = i == 5
    r[idx] = v[idx]
    g[idx] = p[idx]
    b[idx] = q[idx]

    idx = s == 0
    r[idx] = v[idx]
    g[idx] = v[idx]
    b[idx] = v[idx]

    rgb = np.stack([r, g, b], axis=-1)

    return rgb.reshape(in_shape)


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
    def __init__(self, led_count=10):
        super().__init__(led_count=led_count)
        self.mask = (200 <= self.frequencies) & (self.frequencies <= 4000)
        self.bin_count = np.sum(self.mask)
        logger.info("bin_count=" + str(self.bin_count))
        self.bin_to_led_ratio = np.ceil(self.bin_count / self.led_count).astype("int")
        logger.info("bin_to_led_ratio=" + str(self.bin_to_led_ratio))
        self.active_led_count = np.ceil(self.bin_count / self.bin_to_led_ratio).astype(
            "int"
        )
        logger.info("active_led_count=" + str(self.active_led_count))
        self.padding = -(self.bin_count % self.bin_to_led_ratio) % self.bin_to_led_ratio
        logger.info("padding=" + str(self.padding))
        self.hues = np.linspace(0, 1, num=self.active_led_count, endpoint=False)

    def update_leds(self, normalized_amplitudes):
        padded_amplitudes = np.pad(
            normalized_amplitudes[self.mask], (0, self.padding), mode="edge"
        )
        frequency_buckets = padded_amplitudes.reshape(-1, self.bin_to_led_ratio)
        brightness_values = np.clip(
            np.mean(
                frequency_buckets,
                axis=1,
            ),
            a_min=0,
            a_max=1,
        )
        # brightness_values **= 2
        hsv_colors = np.stack(
            (self.hues, np.ones(len(self.hues)), brightness_values), axis=1
        )
        rgb_colors = (hsv_to_rgb(hsv_colors) * 255).astype('uint')
        r, g, b = np.hsplit(rgb_colors, 3)
        bit_colors = r << 16 | g << 8 | b
        for i, color in enumerate(bit_colors):
            self.strip.setPixelColor(i, int(color))
        self.strip.show()


def main():
    visualizer = FrequencyWaveVisualizer(led_count=150)

    try:
        for line in sys.stdin:
            data = np.frombuffer(base64.b64decode(line), dtype="int16")
            visualizer.update(data)

    except KeyboardInterrupt:
        visualizer.turn_off_leds()


if __name__ == "__main__":
    main()
