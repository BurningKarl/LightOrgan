import logging
from logzero import logger


from visualizers.highlevel import (
    StftBrightnessVisualizer,
    FrequencyBandsVisualizer,
    FrequencyWaveVisualizer,
)
from visualizers.leds import ColorsFactory


logger.setLevel(logging.DEBUG)
logger.info("Libraries loaded")


def main():
    visualizer = FrequencyWaveVisualizer(
        rgb_colors_factory=ColorsFactory.RAINBOW,
    )

    try:
        visualizer.run()
    except KeyboardInterrupt:
        visualizer.turn_off_leds()


if __name__ == "__main__":
    main()
