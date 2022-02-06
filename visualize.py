import json
from logzero import logger
import os
import sys


from visualizers.highlevel import (
    FrequencyVisualizer,
    FrequencyBandsVisualizer,
)
from visualizers.leds import ColorFactory


def main():
    config = json.loads(os.environ["LIGHT_ORGAN_CONFIG"])
    logger.setLevel(config["log_level"])

    logger.info("Libraries loaded")

    visualizer = FrequencyVisualizer(
        led_count=config["led_count"],
        sample_rate=config["sample_rate"],
        buffer_size=config["buffer_size"],
        chunk_size=config["chunk_size"],
        rgb_color_factory=ColorFactory.RAINBOW,
    )

    ## visualizer = FrequencyBandsVisualizer(
    ##     led_count=config["led_count"],
    ##     sample_rate=config["sample_rate"],
    ##     buffer_size=config["buffer_size"],
    ##     chunk_size=config["chunk_size"],
    ## )

    # Signal run.py that the audio capturing can start
    message = {"status": "INITIALIZED", "pid": os.getpid()}
    print(json.dumps(message), file=sys.stdout)

    try:
        visualizer.run()
    except KeyboardInterrupt:
        visualizer.turn_off_leds()


if __name__ == "__main__":
    main()
