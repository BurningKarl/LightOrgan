import alsaaudio
import base64
from logzero import logger
import sys


FRAMERATE = 44100  # Frames per second
CHUNK_SIZE = 44100 // 50  # Frames per chunk


def open_capture_device(framerate, chunk_size):
    return alsaaudio.PCM(
        type=alsaaudio.PCM_CAPTURE,
        format=alsaaudio.PCM_FORMAT_S16_LE,
        channels=1,
        rate=framerate,
        periodsize=chunk_size,
    )


def main():
    capture_device = open_capture_device(framerate=FRAMERATE, chunk_size=CHUNK_SIZE)

    logger.info("PCM set up")

    while True:
        try:
            data_length, data = capture_device.read()
        except KeyboardInterrupt:
            break

        print(base64.b64encode(data).decode("ascii"), file=sys.stdout)


if __name__ == "__main__":
    main()
