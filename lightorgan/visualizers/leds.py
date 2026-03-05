import colorsys
import librosa
from logzero import logger
import numpy as np
import rpi_ws281x


from .base import Visualizer


class ColorFactory:
    @staticmethod
    def WHITE(visualizer):
        return [(1, 1, 1) for _ in range(visualizer.led_count)]

    @staticmethod
    def RAINBOW(visualizer):
        return [
            colorsys.hsv_to_rgb(hue, 1, 1)
            for hue in np.linspace(0, 1, visualizer.led_count, endpoint=False)
        ]

    @staticmethod
    def RAINBOW_OCTAVES(visualizer): # Only for FrequencyVisualizer
        led_colors = np.array(
            [(1, 1, 1) for _ in range(visualizer.led_count)], dtype=np.float64
        )

        color_ranges = [
            (
                librosa.note_to_hz(f"C{i+1}"),
                librosa.note_to_hz(f"C{i+2}"),
                colorsys.hsv_to_rgb(i/7, 1, 1),
            )
            for i in range(7)
        ]
        bucket_midpoints = np.array([
            np.sqrt(visualizer.boundaries[i] * visualizer.boundaries[i+1])
            for i in range(visualizer.led_count)
        ])

        for (low, high, rgb) in color_ranges:
            led_colors[(low <= bucket_midpoints) & (bucket_midpoints < high)] = rgb

        return led_colors


class BrightnessVisualizer(Visualizer):
    def __init__(self, *, rgb_color_factory=ColorFactory.WHITE, **kwargs):
        super().__init__(**kwargs)
        self.rgb_color_factory = rgb_color_factory
        self._led_base_colors = None  # Delay initialization until first use

    @property
    def led_base_colors(self):
        if self._led_base_colors is None:
            self._led_base_colors = np.array(
                self.rgb_color_factory(self), dtype=np.float64
            )
        return self._led_base_colors

    def set_led_brightness_values(self, brightness_values):
        colors = np.clip(brightness_values, 0, 1).reshape(-1, 1) * self.led_base_colors
        bit_colors = [
            rpi_ws281x.Color(round(red * 255), round(green * 255), round(blue * 255))
            for (red, green, blue) in colors
        ]
        for i, bit_color in enumerate(bit_colors, start=self.led_offset):
            self.strip.setPixelColor(i, bit_color)
