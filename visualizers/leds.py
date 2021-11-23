import colorsys
from logzero import logger
import numpy as np
import rpi_ws281x


from .base import Visualizer


class ColorsFactory:
    @staticmethod
    def WHITE(led_count):
        return [(1, 1, 1) for _ in range(led_count)]

    @staticmethod
    def RAINBOW(led_count):
        return [
            colorsys.hsv_to_rgb(hue, 1, 1)
            for hue in np.linspace(0, 1, led_count, endpoint=False)
        ]


class BrightnessVisualizer(Visualizer):
    def __init__(self, *, rgb_colors_factory=ColorsFactory.WHITE, **kwargs):
        super().__init__(**kwargs)
        self.rgb_colors = np.array(rgb_colors_factory(self.led_count), dtype=np.float64)

    def set_led_brightness_values(self, brightness_values):
        colors = np.clip(brightness_values, 0, 1).reshape(-1, 1) * self.rgb_colors
        bit_colors = [
            rpi_ws281x.Color(round(red * 255), round(green * 255), round(blue * 255))
            for (red, green, blue) in colors
        ]
        for i, bit_color in enumerate(bit_colors):
            self.strip.setPixelColor(i, bit_color)
