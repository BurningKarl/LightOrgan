import time
import alsaaudio
import numpy as np
import scipy

print('Libraries loaded')

NUMBER_OF_CHANNELS = 1
FRAMERATE = 44100
FORMAT = alsaaudio.PCM_FORMAT_S16_LE
CHUNK_SIZE = 2048
FFT_SIZE = 2048 # Number of frames included in FFT

input_pcm = alsaaudio.PCM(alsaaudio.PCM_CAPTURE)
input_pcm.setchannels(NUMBER_OF_CHANNELS)
input_pcm.setrate(FRAMERATE)
input_pcm.setformat(FORMAT)
input_pcm.setperiodsize(CHUNK_SIZE)

print('PCM set up')

signal = np.zeros(FFT_SIZE)
frequencies = scipy.fft.fftfreq(signal.size, 1/FRAMERATE)
print('Max frequency:', frequencies[len(frequencies)//2 - 1])

# Human hearing range: 20Hz to 20,000Hz
low_range = (20 < frequencies) & (frequencies < 200)
low_range_size = sum(low_range)
mid_range = (200 < frequencies) & (frequencies < 2000)
mid_range_size = sum(mid_range)
high_range = (2000 < frequencies) & (frequencies < 20000)
high_range_size = sum(high_range)

print('Number of indices in low_range', low_range_size)
print('Number of indices in mid_range', mid_range_size)
print('Number of indices in high_range', high_range_size)

print('#'*10)

while True:
    data_length, data = input_pcm.read()
    if data_length:
        #print('Data recieved', data_length, data)
        signal = np.roll(signal, -data_length)
        signal[-data_length:] = np.frombuffer(data, dtype='int16')
        fft = abs(scipy.fft.fft(signal))
        # Average over the specified ranges
        print(f'{sum(fft[low_range])/low_range_size / 2000000}',
              f'{sum(fft[mid_range])/mid_range_size /  500000}',
              f'{sum(fft[high_range])/high_range_size / 50000}')
        #print(f'{max(fft[low_range]):08.0f}',
        #      f'{max(fft[mid_range]):08.0f}',
        #      f'{max(fft[high_range]):08.0f}')
