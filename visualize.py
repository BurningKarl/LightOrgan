import json
from logzero import logger
import os
import sys


from visualizers.highlevel import (
    FrequencyVisualizer,
    FrequencyBandsVisualizer,
)
from visualizers.leds import ColorsFactory


def main():
    config = json.loads(os.environ["LIGHT_ORGAN_CONFIG"])
    logger.setLevel(config.pop("log_level"))

    logger.info("Libraries loaded")

    visualizer = FrequencyVisualizer(
        **config,
        rgb_colors_factory=ColorsFactory.RAINBOW,
    )

    ## visualizer = FrequencyBandsVisualizer(
    ##     **config,
    ## )

    # Signal run.py that the audio capturing can start
    print("INITIALIZED", file=sys.stdout)

    try:
        visualizer.run()
    except KeyboardInterrupt:
        visualizer.turn_off_leds()


if __name__ == "__main__":
    main()
