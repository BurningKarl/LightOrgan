import base64
import colorsys
import easing_functions
import functools
import librosa
import logging
from logzero import logger
import multiprocessing
import numpy as np
from rpi_ws281x import PixelStrip, Color
import scipy.fft
import sys
import time

logger.setLevel(logging.DEBUG)
logger.info("Libraries loaded")


REPORT_CYCLE = 50


def clip(value, lower=0, upper=1):
    return lower if value < lower else upper if value > upper else value


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


class Visualizer:
    # LED strip configuration:
    LED_PIN = 21
    # LED_PIN = 10  # GPIO pin connected to the pixels (10 uses SPI /dev/spidev0.0).
    LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
    LED_DMA = 10  # DMA channel to use for generating signal (try 10)
    LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
    LED_INVERT = (
        False  # True to invert the signal (when using NPN transistor level shift)
    )
    LED_CHANNEL = 0  # set to '1' for GPIOs 13, 19, 41, 45 or 53

    def __init__(self, led_count=10):
        super().__init__()
        self.led_count = led_count

        # Create NeoPixel object with appropriate configuration.
        self.strip = PixelStrip(
            led_count,
            self.LED_PIN,
            self.LED_FREQ_HZ,
            self.LED_DMA,
            self.LED_INVERT,
            self.LED_BRIGHTNESS,
            self.LED_CHANNEL,
        )

        # Intialize the library (must be called once before other functions).
        self.strip.begin()
        logger.info("Strip intialized")

        self.raw_audio_chunks = multiprocessing.Queue()
        self.processed_audio = multiprocessing.Queue()

        self.audio_processing_timer = Timer()
        self.led_timer = Timer()

    def turn_off_leds(self):
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, Color(0, 0, 0))
        self.strip.show()

    def process_audio_chunk(self, chunk):
        # This function should be overwritten by the subclass to perform any audio
        # processing needed. There are no restrictions on the type of data returned
        # here. It is passed as is to set_led_colors.
        return chunk

    def set_led_colors(self, processed_audio):
        # This function should be overwritten by the subclass to set the color of each
        # LED based on the processed audio data returned by process_audio_chunk.
        for i in range(self.led_count):
            self.strip.setPixelColor(i, Color(255, 255, 255))

    def _process_audio(self):
        while True:
            chunk = self.raw_audio_chunks.get()

            queue_size = self.raw_audio_chunks.qsize()
            if queue_size > 1:
                logger.warning(
                    f"More audio chunks available than can be processed: {queue_size}"
                )

            with self.audio_processing_timer:
                processed = self.process_audio_chunk(chunk)

            self.processed_audio.put(processed)

    def _update_leds(self):
        while True:
            data = self.processed_audio.get()

            with self.led_timer:
                self.set_led_colors(data)
                self.strip.show()

    def run(self):
        try:
            processes = (
                multiprocessing.Process(target=self._process_audio, daemon=True),
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

                if logger.isEnabledFor(logging.DEBUG) and i % REPORT_CYCLE == 0:
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


class FrequencyBandsVisualizer(Visualizer):
    FRAMERATE = 44100  # Number of frames per second
    FFT_SIZE = 4096  # Number of frames included in the FFT
    MAX_BRIGHTNESS_AMPLITUDE = 3_000_000
    COLORS = [
        (2 / 3 + 0.025, 1.00, 1),  # Pure blue
        (0 / 3, 1.00, 1),  # Pure red
        (1 / 3 - 0.025, 1.00, 1),  # Pure green
    ]

    def __init__(self, leds_per_band=4):
        led_count = leds_per_band * 3
        super().__init__(led_count=led_count)
        self.signal = np.zeros(self.FFT_SIZE, dtype=np.float64)
        self.frequencies = librosa.fft_frequencies(
            sr=self.FRAMERATE, n_fft=self.FFT_SIZE
        )
        self.leds_per_band = leds_per_band

        # Human hearing range: 20Hz to 20,000Hz
        # Frequency table
        # Name            Range (in Hz)  Use
        # Sub-bass        20 - 60        Felt, sense of power
        # Bass            60 - 250       Fundamental notes
        # Low midrange    250 - 500      Bass instruments
        # Midrange        500 - 2000     Instruments & vocals
        # Upper midrange  2000 - 4000    Percussion & vocals
        # Presence        4000 - 6000    Clarity & defintion
        # Brilliance      6000 - 20000   Sparkle
        self.band_masks = [
            (250 < self.frequencies) & (self.frequencies <= 500),
            (500 < self.frequencies) & (self.frequencies <= 2000),
            (2000 < self.frequencies) & (self.frequencies <= 4000),
        ]
        self.band_sizes = [np.sum(mask) for mask in self.band_masks]

    def update(self, new_data):
        self.signal = np.concatenate((self.signal[len(new_data) :], new_data))
        amplitudes = np.abs(
            librosa.stft(self.signal, n_fft=self.FFT_SIZE, center=False)
        ).reshape(-1)
        self.update_leds(amplitudes / self.MAX_BRIGHTNESS_AMPLITUDE)

    def update_leds(self, normalized_amplitudes):
        brightness_values = [
            clip(np.sum(normalized_amplitudes[mask]) / size, a_min=0, a_max=1)
            for mask, size in zip(self.band_masks, self.band_sizes)
        ]

        for color_index, (base_color, value) in enumerate(
            zip(self.COLORS, brightness_values)
        ):
            hsv_color = base_color[:2] + (value,)
            rgb_color = colorsys.hsv_to_rgb(*hsv_color)
            led_color = Color(*tuple(round(c * 255) for c in rgb_color))
            offset = color_index * self.leds_per_band
            for i in range(self.leds_per_band):
                self.strip.setPixelColor(offset + i, led_color)
        self.strip.show()


class FrequencyWaveVisualizer(Visualizer):
    FRAMERATE = 44100  # Number of frames per second
    FFT_SIZE = 4096  # Number of frames included in the FFT
    MAX_BRIGHTNESS_AMPLITUDE = 1_000_000

    def __init__(
        self,
        num_octaves=8,  # Must be <= 12 for FFT_SIZE=4096
        leds_per_octave=2,
        min_frequency=librosa.note_to_hz("C1"),
        easing_factory=easing_functions.LinearInOut,
    ):
        super().__init__(led_count=num_octaves * leds_per_octave)
        self.num_octaves = num_octaves
        self.leds_per_octave = leds_per_octave
        self.min_frequency = min_frequency

        self.signal = np.zeros(self.FFT_SIZE, dtype=np.float64)
        # Somehow the first call to librosa.cqt takes longer than all
        # subsequent ones, so we trigger this here
        librosa.cqt(
            self.signal,
            sr=self.FRAMERATE,
            hop_length=self.FFT_SIZE * 2,
            fmin=self.min_frequency,
            n_bins=self.led_count,
            bins_per_octave=self.leds_per_octave,
        )

        frequencies = librosa.cqt_frequencies(
            n_bins=self.led_count,
            fmin=self.min_frequency,
            bins_per_octave=self.leds_per_octave,
        )
        logger.info(f"frequencies={frequencies}")

        self.hues = np.linspace(0, 1, num=self.led_count, endpoint=False)

        self.easing_function = easing_factory(start=0, end=1, duration=1)

    def update(self, new_data):
        self.signal = np.concatenate((self.signal[len(new_data) :], new_data))
        amplitudes = np.abs(
            librosa.cqt(
                self.signal,
                sr=self.FRAMERATE,
                hop_length=self.FFT_SIZE * 2,
                fmin=self.min_frequency,
                n_bins=self.led_count,
                bins_per_octave=self.leds_per_octave,
            )
        ).reshape(-1)
        self.update_leds(amplitudes / self.MAX_BRIGHTNESS_AMPLITUDE)

    def update_leds(self, normalized_amplitudes):
        brightness_values = np.clip(normalized_amplitudes, a_min=0, a_max=1)
        brightness_values = [self.easing_function(v) for v in brightness_values]
        logger.debug(
            "brightness_values: "
            + (", ".join([f"{val:0.03f}" for val in brightness_values]))
        )

        for i, (hue, brightness) in enumerate(zip(self.hues, brightness_values)):
            rgb_color = colorsys.hsv_to_rgb(hue, 1, brightness)
            led_color = Color(*tuple(round(c * 255) for c in rgb_color))
            self.strip.setPixelColor(i, led_color)
        self.strip.show()


def main():
    # visualizer = FrequencyWaveVisualizer(
    #     num_octaves=8, leds_per_octave=2, easing_factory=easing_functions.LinearInOut
    # )
    visualizer = Visualizer(led_count=10)

    try:
        visualizer.run()
    except KeyboardInterrupt:
        visualizer.turn_off_leds()


if __name__ == "__main__":
    main()
