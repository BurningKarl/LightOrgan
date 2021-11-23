import abc
import base64
import logging
from logzero import logger
import multiprocessing
import numpy as np
import rpi_ws281x
import sys
import time


class Timer:
    def __init__(self):
        self.shared = multiprocessing.Value("d", 0)

    @property
    def value(self):
        return self.shared.value

    def __enter__(self):
        self.start_time = time.monotonic()

    def __exit__(self, exc_type, exc_val, exc_tb):
        with self.shared.get_lock():
            self.shared.value += time.monotonic() - self.start_time


class Visualizer(abc.ABC):
    LED_PIN = 21  # see README
    REPORT_INTERVAL = 50  # Print report every ... updates

    def __init__(self, *, led_count=10):
        super().__init__()
        self.led_count = led_count

        # Create NeoPixel object with appropriate configuration.
        self.strip = rpi_ws281x.PixelStrip(num=led_count, pin=self.LED_PIN)

        # Intialize the library (must be called once before other functions).
        self.strip.begin()
        logger.info("Strip intialized")

        self.raw_audio_chunks = multiprocessing.Queue()
        self.processed_audio = multiprocessing.Queue()

        self.audio_processing_timer = Timer()
        self.led_timer = Timer()

    def turn_off_leds(self):
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, rpi_ws281x.Color(0, 0, 0))
        self.strip.show()

    @abc.abstractmethod
    def process_audio_chunk(self, chunk):
        # This function needs to be overwritten by the subclass to perform any audio
        # processing needed. There are no restrictions on the type of data returned
        # here. It is passed as is to set_led_colors.
        return chunk

    @abc.abstractmethod
    def set_led_colors(self, processed_audio):
        # This function needs to be overwritten by the subclass to set the color of
        # each LED based on the processed audio data returned by process_audio_chunk.
        pass

    def _process_audio(self):
        while True:
            chunk = self.raw_audio_chunks.get()

            queue_size = self.raw_audio_chunks.qsize()
            if queue_size > 3:
                logger.warning(
                    f"More audio chunks available than can be processed: {queue_size}"
                )

            with self.audio_processing_timer:
                processed = self.process_audio_chunk(chunk)

            self.processed_audio.put(processed)

    def _update_leds(self):
        while True:
            data = self.processed_audio.get()

            queue_size = self.processed_audio.qsize()
            if queue_size > 3:
                logger.warning(
                    f"More processed audio chunks available than can be processed: "
                    f"{queue_size}"
                )

            with self.led_timer:
                self.set_led_colors(data)
                self.strip.show()

    def run(self):
        try:
            processes = (
                multiprocessing.Process(target=self._process_audio),
                multiprocessing.Process(target=self._update_leds, daemon=True),
            )
            for process in processes:
                process.start()

            logger.info("Processes started")

            sys.stdin.readline()  # Skip first line to get accurate timing results
            start_time = time.monotonic()
            for i, line in enumerate(sys.stdin, start=1):
                binary_data = base64.b64decode(line)
                chunk = np.frombuffer(binary_data, dtype=np.int16).astype(np.float64)
                self.raw_audio_chunks.put(chunk)

                if logger.isEnabledFor(logging.DEBUG) and i % self.REPORT_INTERVAL == 0:
                    total_time = time.monotonic() - start_time
                    audio_utilitization = self.audio_processing_timer.value / total_time
                    led_utilitization = self.led_timer.value / total_time
                    logger.debug(
                        f"Total: {total_time:.2f} s, "
                        f"Audio processing: {audio_utilitization:.2%}, "
                        f"LED strip: {led_utilitization:.2%}"
                    )

        finally:
            for process in processes:
                process.terminate()
