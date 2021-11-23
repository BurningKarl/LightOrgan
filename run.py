import argparse
import json
import logging
from logzero import logger
import os
import pathlib
import subprocess
import sys


def parse_options():
    parser = argparse.ArgumentParser(
        prog="python " + sys.argv[0],
        description="Controls a WS2812B LED strip so that it reacts to whatever audio "
        "is currently playing.",
    )
    parser.add_argument(
        "--led-count",
        metavar="COUNT",
        type=int,
        default=9,
        help="number of LEDs used (default: 9)",
    )
    parser.add_argument(
        "--update-freq",
        metavar="FREQ",
        type=float,
        default=30,
        help="number of times per second new audio data is retrieved from ALSA "
        "(default: 30.0)",
    )
    parser.add_argument(
        "--sample-rate",
        metavar="SR",
        type=int,
        default=44100,
        help="sample rate captured from ALSA (default: 44100)",
    )
    parser.add_argument(
        "--buffer-size",
        metavar="SIZE",
        type=int,
        default=2 ** 13,
        help="size of buffer that holds the most recent samples and is analyzed at "
        "each update (default: 2^13 = 8192)",
    )
    parser.add_argument(
        "--log-level",
        metavar="LEVEL",
        default=logging.INFO,
        type=lambda x: logging._nameToLevel[x],
        help="the logging level (default: INFO)",
    )

    args = vars(parser.parse_args())

    # Replace update_freq by the corresponding chunk_size
    args["chunk_size"] = int(args["sample_rate"] / args["update_freq"])
    del args["update_freq"]

    return args


def main():
    config = parse_options()
    logger.setLevel(config["log_level"])

    logger.debug(f"Config options: {config}")

    # The following is similar to the bash command
    #    python -u scripts/capture_audio.py | sudo python visualize.py
    #
    # The audio signal output of the Raspberry Pi for the user pi can only be captured
    # as the user pi, but at the same time to control the LED strip access to
    # `/dev/mem` is needed which is only given to the root user. The solution is to
    # split the two tasks up into two scripts: `capture_audio.py` and `visualize.py`.
    # The communication works by piping stdout of one to stdin of the other.
    #
    # The `-u` option forces python to not buffer the stdout stream. If omitted, the
    # data is sent in chunks and the LED strip will not react in real time.

    here = pathlib.Path(__file__).resolve().parent
    python = sys.executable

    environment_variables = os.environ.copy()
    environment_variables["LIGHT_ORGAN_CONFIG"] = json.dumps(config)

    visualize_process = subprocess.Popen(
        ["sudo", "--preserve-env=LIGHT_ORGAN_CONFIG", python, here / "visualize.py"],
        env=environment_variables,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )

    # Start capturing audio after initialization is done
    while visualize_process.stdout.readline() != b"INITIALIZED\n":
        pass

    capture_audio_process = subprocess.Popen(
        [python, "-u", here / "scripts" / "capture_audio.py"],
        env=environment_variables,
        stdout=visualize_process.stdin,
    )

    try:
        capture_audio_process.wait()
    except KeyboardInterrupt:
        # The processes handle Ctrl+C themselves
        pass


if __name__ == "__main__":
    main()
