import abc
import base64
import colorsys
import easing_functions
import functools
import logging
from logzero import logger
import math
import multiprocessing
import numpy as np
import os
from rpi_ws281x import PixelStrip, Color
import scipy.fft
import sys
import time
import warnings

os.environ["LIBROSA_CACHE_DIR"] = "/tmp/librosa_cache"
import librosa


logger.setLevel(logging.DEBUG)
logger.info("Libraries loaded")


REPORT_CYCLE = 50


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

    def __init__(self, led_count):
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


class StftVisualizer(Visualizer):
    FRAMERATE = 44100  # Number of frames per second
    FFT_SIZE = 2 ** 13  # Number of frames included in the FFT
    MAX_BRIGHTNESS_AMPLITUDE = 3_000_000

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signal = np.zeros(self.FFT_SIZE, dtype=np.float64)
        self.frequencies = librosa.fft_frequencies(
            sr=self.FRAMERATE, n_fft=self.FFT_SIZE
        )

    def process_audio_chunk(self, chunk):
        if len(chunk) > self.signal.shape[0]:
            raise RuntimeError("The audio chunk is too large, please increase FFT_SIZE")

        self.signal = np.concatenate((self.signal[len(chunk) :], chunk))
        amplitudes = np.abs(
            librosa.stft(self.signal, n_fft=self.FFT_SIZE, center=False)
        ).reshape(-1)
        return amplitudes / self.MAX_BRIGHTNESS_AMPLITUDE


class IirtVisualizer(Visualizer):
    FRAMERATE = 44100  # Number of frames per second
    FFT_SIZE = 2 ** 13  # Number of frames included in the FFT
    MAX_BRIGHTNESS_AMPLITUDE = 1_000_000_000

    @staticmethod
    def generate_filter_bank(frequencies, filter_layout):
        # This emulates the behavior of librosa.mr_frequencies but adapts to an
        # arbitrary number of frequencies in each octave. See page 52 of
        #     Müller, M. (2007). Information Retrieval for Music and Motion.
        #     doi:10.1007/978-3-540-74048-3
        if np.min(frequencies) < librosa.midi_to_hz(21):
            raise RuntimeError(
                "The minimum frequency cannot be lower than " + librosa.midi_to_note(21)
            )
        if np.max(frequencies) > librosa.midi_to_hz(108):
            raise RuntimeError(
                "The maximum frequency cannot be higher than "
                + librosa.midi_to_note(108)
            )

        sample_rates = np.full(frequencies.shape, 22050)
        sample_rates[frequencies < librosa.midi_to_hz(93)] = 4410
        sample_rates[frequencies < librosa.midi_to_hz(57)] = 882

        # Generate the corresponding filters, sample_rates stay unchanged
        filterbank, sample_rates = librosa.filters.semitone_filterbank(
            center_freqs=frequencies,
            sample_rates=sample_rates,
            flayout=filter_layout,
        )

        return filterbank, sample_rates

    def __init__(
        self,
        *args,
        num_octaves=5,
        leds_per_octave=2,
        min_frequency=librosa.note_to_hz("C3"),
        filter_layout="ba",
        **kwargs,
    ):
        super().__init__(*args, led_count=num_octaves * leds_per_octave, **kwargs)
        logger.debug(f"led_count={self.led_count}")
        self.num_octaves = num_octaves
        self.leds_per_octave = leds_per_octave
        self.min_frequency = min_frequency
        self.filter_layout = filter_layout

        log_min_frequency = np.log2(min_frequency)
        self.frequencies = np.logspace(
            start=log_min_frequency,
            stop=log_min_frequency + self.num_octaves,
            num=self.led_count,
            endpoint=False,
            base=2,
        )

        self.filterbank, self.sample_rates = self.generate_filter_bank(
            self.frequencies, self.filter_layout
        )
        self._compute_filter_power = {
            "ba": self._compute_filter_power_ba,
            "sos": self._compute_filter_power_sos,
        }[self.filter_layout]

        self.signal = np.zeros(self.FFT_SIZE, dtype=np.float64)

    def _process_audio(self):
        # A small hack to initialize the new pool inside the _process_audio process
        with multiprocessing.Pool() as pool:
            self.process_audio_chunk = functools.partial(self.process_audio_chunk, pool=pool)
            super()._process_audio()

    @staticmethod
    def _compute_filter_power_ba(resampled_signal, cur_sr, cur_filter):
        cur_filter_output = scipy.signal.filtfilt(
            cur_filter[0], cur_filter[1], resampled_signal[cur_sr], padtype=None
        )
        return np.sum(cur_filter_output ** 2)

    @staticmethod
    def _compute_filter_power_sos(resampled_signal, cur_sr, cur_filter):
        cur_filter_output = scipy.signal.sosfiltfilt(
            cur_filter, resampled_signal[cur_sr], padtype=None
        )
        return np.sum(cur_filter_output ** 2)

    def process_audio_chunk(self, chunk, pool):
        if len(chunk) > self.signal.shape[0]:
            raise RuntimeError("The audio chunk is too large, please increase FFT_SIZE")

        self.signal = np.concatenate((self.signal[len(chunk) :], chunk))

        # Adapted from `librosa.iirt`
        resampled_signal = {
            cur_sr: librosa.resample(
                self.signal, self.FRAMERATE, cur_sr, res_type="polyphase"
            )
            for cur_sr in np.unique(self.sample_rates)
        }

        # The same as calling self._apply_filter(resampled_signal, cur_sr, cur_filter)
        # for every (cur_sr, cur_filter) in zip(self.sample_rates, self.filterbank)
        amplitudes = (self.FRAMERATE / self.sample_rates) * pool.starmap(
            functools.partial(self._compute_filter_power, resampled_signal),
            zip(self.sample_rates, self.filterbank),
            chunksize=math.ceil(len(self.sample_rates) / pool._processes),
        )

        return amplitudes / self.MAX_BRIGHTNESS_AMPLITUDE


class ColorsFactory:
    @staticmethod
    def RAINBOW(led_count):
        return [
            colorsys.hsv_to_rgb(hue, 1, 1)
            for hue in np.linspace(0, 1, led_count, endpoint=False)
        ]


class BrightnessVisualizer(Visualizer):
    def __init__(self, *args, rgb_colors_factory=None, **kwargs):
        super().__init__(*args, **kwargs)
        if rgb_colors_factory is not None:
            self.rgb_colors = rgb_colors_factory(self.led_count)
        else:
            self.rgb_colors = [(1, 1, 1) for _ in range(self.led_count)]
        self.rgb_colors = np.array(self.rgb_colors, dtype=np.float64)

    def set_led_brightness_values(self, brightness_values):
        colors = np.clip(brightness_values, 0, 1).reshape(-1, 1) * self.rgb_colors
        bit_colors = [
            Color(round(red * 255), round(green * 255), round(blue * 255))
            for (red, green, blue) in colors
        ]
        for i, bit_color in enumerate(bit_colors):
            self.strip.setPixelColor(i, bit_color)


class StftBrightnessVisualizer(StftVisualizer, BrightnessVisualizer):
    def set_led_colors(self, normalized_amplitudes):
        # Simple downsampling
        data_length = normalized_amplitudes.shape[0]
        brightness_values = (
            normalized_amplitudes[: data_length - data_length % self.led_count]
            .reshape(self.led_count, -1)
            .mean(axis=1)
        )
        self.set_led_brightness_values(brightness_values)


class FrequencyBandsVisualizer(StftVisualizer, BrightnessVisualizer):
    COLORS = [
        (0, 0, 1),  # Pure blue
        (1, 0, 0),  # Pure red
        (0, 1, 0),  # Pure green
    ]

    def __init__(self, leds_per_band=4):
        super().__init__(
            led_count=leds_per_band * len(self.COLORS),
            rgb_colors_factory=lambda _: np.repeat(self.COLORS, leds_per_band, axis=0),
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
        # Presence        4000 - 6000    Clarity & definition
        # Brilliance      6000 - 20000   Sparkle
        self.band_masks = [
            (250 < self.frequencies) & (self.frequencies <= 500),
            (500 < self.frequencies) & (self.frequencies <= 2000),
            (2000 < self.frequencies) & (self.frequencies <= 4000),
        ]
        self.band_sizes = [np.sum(mask) for mask in self.band_masks]

    def set_led_colors(self, normalized_amplitudes):
        brightness_values = [
            np.sum(normalized_amplitudes[mask]) / size
            for mask, size in zip(self.band_masks, self.band_sizes)
        ]
        brightness_values = np.repeat(brightness_values, self.leds_per_band)
        self.set_led_brightness_values(brightness_values)


class FrequencyWaveVisualizer(IirtVisualizer, BrightnessVisualizer):
    def set_led_colors(self, normalized_amplitudes):
        self.set_led_brightness_values(normalized_amplitudes)


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
