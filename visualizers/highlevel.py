from logzero import logger
import numpy as np
import scipy.integrate


from .audio import StftVisualizer, IirtVisualizer
from .leds import BrightnessVisualizer


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


class FrequencyVisualizer(StftVisualizer, BrightnessVisualizer):
    def __init__(
        self,
        *,
        min_frequency=250,  # ~ B3
        max_frequency=4000,  # ~ B7
        logarithmic_spacing=True,
        **kwargs,
    ):
        super().__init__(**kwargs)

        if logarithmic_spacing:
            self.boundaries = np.logspace(
                start=np.log10(min_frequency),
                stop=np.log10(max_frequency),
                base=10.0,
                num=self.led_count + 1,
            )
        else:
            self.boundaries = np.linspace(
                start=min_frequency,
                stop=max_frequency,
                num=self.led_count + 1,
            )

    @staticmethod
    def interpolate_integral(x_new, xs, ys):
        """
        Calculates the integral from xs[0] to t (for any t <= xs[-1]) of the
        piecewise linear interpolant of (xs[0], ys[0]), ...
        """
        indices = np.searchsorted(xs, x_new, side="right") - 1
        if (indices < 0).any():
            raise ValueError("A value in x_new is below the interpolation range.")
        if (x_new > np.max(xs)).any():
            raise ValueError("A value in x_new is above the interpolation range.")

        # Compute the desired values for all t in xs
        cumulative = scipy.integrate.cumulative_trapezoid(y=ys, x=xs, initial=0)

        # Compute the slope of each linear segment
        # A zero is added at the end to avoid errors when np.max(xs) is in x_new
        slopes = np.concatenate((np.diff(ys) / np.diff(xs), [0]))

        # Look up the integral from 0 to the largest element of xs smaller than t and
        # then add the remaining integral (which is a quadratic of the remainder)
        x_remainder = x_new - xs[indices]
        return (
            cumulative[indices]
            + (slopes[indices] / 2) * x_remainder ** 2
            + ys[indices] * x_remainder
        )

    def set_led_colors(self, normalized_amplitudes):
        average_amplitudes = (
            np.diff(
                self.interpolate_integral(
                    x_new=self.boundaries,
                    xs=self.frequencies,
                    ys=normalized_amplitudes,
                )
            )
            / np.diff(self.boundaries)
        )
        self.set_led_brightness_values(average_amplitudes)


class FrequencyBandsVisualizer(StftVisualizer, BrightnessVisualizer):
    COLORS = [
        (0, 0, 1),  # Pure blue
        (1, 0, 0),  # Pure red
        (0, 1, 0),  # Pure green
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.leds_per_band = self.led_count // len(self.COLORS)
        if self.led_count != self.leds_per_band * len(self.COLORS):
            self.led_count = self.leds_per_band * len(self.COLORS)
            logger.warning(
                f"led_count is not a multiple of {len(self.COLORS)}, "
                f"it was reduced to {self.leds_per_band * len(self.COLORS)}"
            )

        # Replace LED colors by custom ones
        self.rgb_colors = np.repeat(self.COLORS, self.leds_per_band, axis=0)

        self.band_masks = [
            (250 < self.frequencies) & (self.frequencies <= 500),  # Low midrange
            (500 < self.frequencies) & (self.frequencies <= 2000),  # Midrange
            (2000 < self.frequencies) & (self.frequencies <= 4000),  # Upper midrange
        ]
        self.band_sizes = [np.sum(mask) for mask in self.band_masks]

    def set_led_colors(self, normalized_amplitudes):
        brightness_values = [
            np.sum(normalized_amplitudes[mask]) / size
            for mask, size in zip(self.band_masks, self.band_sizes)
        ]
        brightness_values = np.repeat(brightness_values, self.leds_per_band)
        self.set_led_brightness_values(brightness_values)


class IirtBrightnessVisualizer(IirtVisualizer, BrightnessVisualizer):
    def set_led_colors(self, normalized_amplitudes):
        self.set_led_brightness_values(normalized_amplitudes)
