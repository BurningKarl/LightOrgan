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
# Frequency table
# Name            Range (in Hz)  Use
# Sub-bass        20 - 60        Felt, sense of power
# Bass            60 - 250       Fundamental notes
# Low midrange    250 - 500      Bass instruments
# Midrange        500 - 2000     Instruments & vocals
# Upper midrange  2000 - 4000    Percussion & vocals
# Presence        4000 - 6000    Clarity & defintion
# Brilliance      6000 - 20000   Sparkle
low_range = (250 < frequencies) & (frequencies <= 500)
low_range_size = sum(low_range)
mid_range = (500 < frequencies) & (frequencies <= 2000)
mid_range_size = sum(mid_range)
high_range = (2000 < frequencies) & (frequencies <= 4000)
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
        print(f'{sum(fft[low_range])/low_range_size /   600000:0.010f}',
              f'{sum(fft[mid_range])/mid_range_size /   300000:0.010f}',
              f'{sum(fft[high_range])/high_range_size / 150000:0.010f}')
        # The denominators were determined empirically so that the
        # mean over the values over a range of a normal piece of
        # music is close to 0.5. The value of 1 is still exceeded
        # regularly, but I hope this gives a good compromise between
        # the usage of the full range and the fact the range of the
        # output should be 0 to 1
