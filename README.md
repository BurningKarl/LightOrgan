# LightOrgan
A light organ with raspotify and a WS2812B LED strip on a Raspberry Pi

The light organ is able to react to all sounds played as the user pi.
I use it in conjunction with a custom systemd service that is very closely modeled after the one provided by raspotify
to transform the Raspberry Pi into a Spotify player.

## Hardware requirements
1. A Raspberry Pi with Raspbian
1. A WS2812B LED strip or similar

## Steps
1. Clone the repo and install the python libraries in `requirements.txt`
1. Correctly set up the WS2812B LED strip
1. Transform your Raspberry Pi into a Spotify player (optional)
1. Enjoy your light organ by running `python -u realtime_fft.py | sudo venv/bin/python stdin_to_led_strip.py`

## Step 1: Repo and python setup
Clone the repository, setup a python virtual environment and install all the necessary packages
```bash
git clone https://github.com/BurningKarl/LightOrgan.git
cd LightOrgan
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Step 2: WS2812 setup
I used https://github.com/jgarff/rpi_ws281x/blob/master/README.md to help me to set up my WS2812B LED strip. 
I decided to use the PCM method on GPIO 21 (pin 40), because 

> When using PCM you cannot use digital audio devices which use I2S since I2S uses the PCM hardware, but you can use analog audio.

and analog audio is enough for my purposes. 
This also has the advantage that it is very easy to setup: 

* Connect the ground of the LED strip to ground of the raspberry pi
* Connect the 5V of the LED strip to 5V of the raspberry pi
* Connect the dataline of the LED strip to pin 40

At this point nothing should happen. The LEDs will not automatically turn on. 
You can test everything with `sudo venv/bin/python strandtest.py -c` and the first six LEDs will start to light up in various colors and patterns.
The reason I have set `LED_COUNT = 6` is that there is a limit to the number LEDs that you can use simultaneously with the Raspbery Pi as the only power source.
A single LED can use up to 60 mA of current and it depends on the type of Raspberry Pi what currents it allows.
According to [this sheet](https://www.raspberrypi.org/documentation/hardware/raspberrypi/power/README.md) my Raspberry Pi 3B
has a recommend capacity for the power supply unit of 2.5A which I assume to be close to the current the default power supply unit will provide.
Using all 150 LEDs (5m * 30LEDs/m) at the same time leads to a maximum of 9A which is definitely above 2.5A.
You can obviously bypass these problems with an external powersource for the LED strip but if you don't decide to use one be aware!

## Step 3: Raspotify setup
Install [Raspotify](https://github.com/dtcooper/raspotify) as explained in its readme and test it to see if everything
is set up correctly. As stated at the top the light organ will only be able to pick up sounds that are played by the user pi.
This a limitation of the ALSA audio system as far as I can see and it forces us to deactivate the systemd service
that Raspotify comes with and replace it with a systemd user service for the user pi.
The systemd service I successfully used is included in this repository.

```bash
sudo systemctl disable --now raspotify
cp raspotify.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now raspotify
```

Now the Spotify device "raspotify (...)" should also appear as long as the Raspberry Pi is running.
To test whether the sound output of the Spotify Device can be captured by ALSA use

```bash
arecord -d 10 -f cd test.wav
aplay test.wav
```

This should record 10 seconds of CD quality sound to `test.wav` and then play it back to you. 
Of course you need to play some music at the time of the recording.

## Step 4: Enjoy
The audio signal output of the Raspberry Pi for the user pi can only be captured as the user pi 
but at the same time to control the LED strip access to `/dev/mem` is needed which is only given to the root user.
I solved this problem by creating two different python scripts: 
One runs as the user pi and analyzes the audio signal (`realtime_fft.py`) and one runs as root and controls the LED strip (`stdin_to_led_strip.py`).
As the name of the second script suggests, they communicate through stdin and stdout.
The stdout of one script to be directed to the stdin of the second script with piping on the command line.
To use the light organ run
```bash
python -u realtime_fft.py | sudo venv/bin/python stdin_to_led_strip.py
```

At the time of this writing the `realtime_fft.py` script performs the audio analysis and outputs one line for every time step.
Each line consists of multiple values from 0 to 255 that indicate the volume of different parts of the spectrum (low to high frequencies).
The `stdin_to_led_strip.py` then takes these values and uses them as the brightness values for different LEDs and different colors (low frequencies = blue, middle frequencies = red, high frequencies = green).

Note that the `-u` option forces python to not buffer the stdout stream. If omitted, the data is sent in chunks and the LED strip will not react in real time.

## Troubleshooting

### The sound is choppy and slow

This happend to me multiple times during testing. It might be caused by the sound chip overheating, but sometimes I was able to solve it by changing the sound source from raspotify to `aplay test.wav` and back.
