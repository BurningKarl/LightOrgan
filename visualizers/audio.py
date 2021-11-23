import functools
import librosa
from logzero import logger
import math
import multiprocessing
import numpy as np
import scipy


from .base import Visualizer


# The classes StftVisualizer and IirtVisualizer provide process_audio_chunk
# implementations that do audio analysis based on librosa.stft and librosa.iirt
# respectively. Unfortunately, audio analysis based on IIRT is not fast enough even
# though I tried heavily using custom implementations and multiprocessing. On my
# Raspberry Pi 3B the best I could do is about 30 updates per second using 20 LEDs.
# Additionally, this was achieved using filter_layout='ba' which exhibits flickering
# artifacts when tested using rising pure tones.
#
# Therefore, the use of IirtVisualizer is discouraged!


class BufferedAudioVisualizer(Visualizer):
    def __init__(self, *, sample_rate, buffer_size, chunk_size, **kwargs):
        super().__init__(**kwargs)
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.chunk_size = chunk_size

        if self.chunk_size > self.buffer_size:
            raise RuntimeError(
                "The chunk_size can be at most as large as the buffer_size"
            )

        self.buffer = np.zeros(self.buffer_size, dtype=np.float64)

        # Update REPORT_INTERVAL to print every 5 seconds
        self.REPORT_INTERVAL = math.ceil(5 / (self.chunk_size / self.sample_rate))

    def update_buffer(self, chunk):
        if len(chunk) > self.buffer.shape[0]:
            raise RuntimeError(
                "The audio chunk is too large, please increase the buffer size"
            )

        self.buffer = np.concatenate((self.buffer[len(chunk) :], chunk))


class StftVisualizer(BufferedAudioVisualizer):
    MAX_BRIGHTNESS_AMPLITUDE = 3_000_000

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.frequencies = librosa.fft_frequencies(
            sr=self.sample_rate, n_fft=self.buffer_size
        )

    def process_audio_chunk(self, chunk):
        self.update_buffer(chunk)
        amplitudes = np.abs(
            librosa.stft(self.buffer, n_fft=self.buffer_size, center=False)
        ).reshape(-1)
        return amplitudes / self.MAX_BRIGHTNESS_AMPLITUDE


class IirtVisualizer(BufferedAudioVisualizer):
    MAX_BRIGHTNESS_AMPLITUDE = 1_000_000

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
        *,
        num_octaves=4,
        min_frequency=250,
        filter_layout="ba",  # See flayout argument of librosa.iirt
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.num_octaves = num_octaves
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
        self.unique_sample_rates = np.unique(self.sample_rates)

        self._compute_filter_power = {
            "ba": self._compute_filter_power_ba,
            "sos": self._compute_filter_power_sos,
        }[self.filter_layout]

        self.buffer = np.zeros(self.buffer_size, dtype=np.float64)

    def _process_audio(self):
        # A small hack to initialize the new pool inside the _process_audio process
        with multiprocessing.Pool() as pool:
            self.process_audio_chunk = functools.partial(
                self.process_audio_chunk, pool=pool
            )
            super()._process_audio()

    @staticmethod
    def _compute_filter_power_ba(signal, cur_filter):
        cur_filter_output = scipy.signal.filtfilt(cur_filter[0], cur_filter[1], signal)
        return np.mean(cur_filter_output ** 2)

    @staticmethod
    def _compute_filter_power_sos(signal, cur_filter):
        cur_filter_output = scipy.signal.sosfiltfilt(cur_filter, signal)
        return np.mean(cur_filter_output ** 2)

    def process_audio_chunk(self, chunk, pool):
        self.update_buffer(chunk)

        resample_to_sr = functools.partial(
            librosa.resample, self.buffer, self.sample_rate, res_type="polyphase"
        )
        resampled_signal = dict(
            zip(
                self.unique_sample_rates,
                pool.map(resample_to_sr, self.unique_sample_rates),
            )
        )

        amplitudes = np.array(
            pool.starmap(
                self._compute_filter_power,
                (
                    (resampled_signal[cur_sr], cur_filter)
                    for cur_sr, cur_filter in zip(self.sample_rates, self.filterbank)
                ),
                chunksize=math.ceil(len(self.sample_rates) / pool._processes),
            )
        )

        return amplitudes / self.MAX_BRIGHTNESS_AMPLITUDE
