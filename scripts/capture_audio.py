import alsaaudio
import base64
import collections
import json
from logzero import logger
import os
import sys
import time


def open_capture_device(sample_rate, chunk_size):
    return alsaaudio.PCM(
        type=alsaaudio.PCM_CAPTURE,
        mode=alsaaudio.PCM_ASYNC,
        format=alsaaudio.PCM_FORMAT_S16_LE,
        channels=1,
        rate=sample_rate,
        periodsize=chunk_size,
    )


TimedData = collections.namedtuple("TimedData", ["data", "release_time"])


def main():
    config = json.loads(os.environ["LIGHT_ORGAN_CONFIG"])
    logger.setLevel(config["log_level"])

    capture_device = open_capture_device(
        sample_rate=config["sample_rate"], chunk_size=config["chunk_size"]
    )
    logger.info("PCM set up")

    data_queue = []
    while True:
        try:
            data_length, chunk = capture_device.read()
            if data_length > 0:
                data_queue.append(
                    TimedData(
                        data=base64.b64encode(chunk).decode("ascii"),
                        release_time=time.monotonic() + config["delay"],
                    )
                )
            if data_queue and data_queue[0].release_time <= time.monotonic():
                print(data_queue.pop(0).data, file=sys.stdout)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()
