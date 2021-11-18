import alsaaudio
import base64
from logzero import logger
import sys
import time


SAMPLE_RATE = 44100  # Samples per second
CHUNK_SIZE = SAMPLE_RATE // 30  # Samples per chunk


def open_capture_device(sample_rate, chunk_size):
    return alsaaudio.PCM(
        type=alsaaudio.PCM_CAPTURE,
        format=alsaaudio.PCM_FORMAT_S16_LE,
        channels=1,
        rate=sample_rate,
        periodsize=chunk_size,
    )


def main():
    time.sleep(15)
    logger.info("Slept for fifteen seconds")

    capture_device = open_capture_device(sample_rate=SAMPLE_RATE, chunk_size=CHUNK_SIZE)
    logger.info("PCM set up")

    while True:
        try:
            data_length, data = capture_device.read()
        except KeyboardInterrupt:
            break

        print(base64.b64encode(data).decode("ascii"), file=sys.stdout)


if __name__ == "__main__":
    main()
