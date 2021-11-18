from logzero import logger
import numpy as np


from .audio import StftVisualizer, IirtVisualizer
from .leds import ColorsFactory, BrightnessVisualizer


class StftBrightnessVisualizer(StftVisualizer, BrightnessVisualizer):
    def set_led_colors(self, normalized_amplitudes):
        # Simple downsampling
        data_length = normalized_amplitudes.shape[0]
        brightness_values = (
            normalized_amplitudes[: data_length - data_length % self.led_count]
            .reshape(self.led_count, -1)
            .mean(axis=1)
        )
        self.set_led_brightness_values(brightness_values)


class FrequencyBandsVisualizer(StftVisualizer, BrightnessVisualizer):
    COLORS = [
        (0, 0, 1),  # Pure blue
        (1, 0, 0),  # Pure red
        (0, 1, 0),  # Pure green
    ]

    def __init__(self, leds_per_band=4):
        super().__init__(
            led_count=leds_per_band * len(self.COLORS),
            rgb_colors_factory=lambda _: np.repeat(self.COLORS, leds_per_band, axis=0),
        )
        self.leds_per_band = leds_per_band

        # Human hearing range: 20Hz to 20,000Hz
        # Frequency table
        # Name            Range (in Hz)  Use
        # Sub-bass        20 - 60        Felt, sense of power
        # Bass            60 - 250       Fundamental notes
        # Low midrange    250 - 500      Bass instruments
        # Midrange        500 - 2000     Instruments & vocals
        # Upper midrange  2000 - 4000    Percussion & vocals
        # Presence        4000 - 6000    Clarity & definition
        # Brilliance      6000 - 20000   Sparkle
        self.band_masks = [
            (250 < self.frequencies) & (self.frequencies <= 500),
            (500 < self.frequencies) & (self.frequencies <= 2000),
            (2000 < self.frequencies) & (self.frequencies <= 4000),
        ]
        self.band_sizes = [np.sum(mask) for mask in self.band_masks]

    def set_led_colors(self, normalized_amplitudes):
        brightness_values = [
            np.sum(normalized_amplitudes[mask]) / size
            for mask, size in zip(self.band_masks, self.band_sizes)
        ]
        brightness_values = np.repeat(brightness_values, self.leds_per_band)
        self.set_led_brightness_values(brightness_values)


class FrequencyWaveVisualizer(IirtVisualizer, BrightnessVisualizer):
    def set_led_colors(self, normalized_amplitudes):
        self.set_led_brightness_values(normalized_amplitudes)
