import logging
from logzero import logger
import sys


from visualizers.highlevel import (
    StftBrightnessVisualizer,
    FrequencyBandsVisualizer,
    FrequencyWaveVisualizer,
)
from visualizers.leds import ColorsFactory


logger.setLevel(logging.DEBUG)
logger.info("Libraries loaded")


def main():
    visualizer = StftBrightnessVisualizer(
        led_count=10,
        logarithmic_spacing=True,
        rgb_colors_factory=ColorsFactory.RAINBOW,
    )

    # Signal run.py that the audio capturing can start
    print("INITIALIZED", file=sys.stdout)

    try:
        visualizer.run()
    except KeyboardInterrupt:
        visualizer.turn_off_leds()


if __name__ == "__main__":
    main()