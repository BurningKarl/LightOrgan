# light-organ
A light organ with raspotify and a WS2812B LED strip on a Raspberry Pi

The light organ is able to react to all sounds played as the user pi.
I use it in conjunction with a custom systemd service that is very closely modeled after the one provided by raspotify
to transform the Raspberry Pi into a Spotify player.

## Steps
1. Clone the repo and install the python libraries in `requirements.txt`
1. Correctly set up the WS2812B LED strip
1. Install and configure [Raspotify](https://github.com/dtcooper/raspotify) (optional)
1. Enjoy your light organ by running `python -u realtime_fft.py | sudo venv/bin/python stdin_to_led_strip.py`

## Step 1: Repo and python setup
Clone the repository, setup a python virtual environment and install all the necessary packages
```
git clone https://github.com/BurningKarl/light-organ.git
cd light-organ
python3 -m virtualenv venv
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
You can test everything with `python strandtest.py -c` and the first six LEDs will start to light up in various colors and patterns.
The reason I have set `LED_COUNT = 6` is that there is a limit to the number LEDs that you can use simultaneously with the Raspbery Pi as the only power source.
A single LED can use up to 60 mA of current and it depends on the type of Raspberry Pi what currents it allows.
According to [this sheet](https://www.raspberrypi.org/documentation/hardware/raspberrypi/power/README.md) my Raspberry Pi 3B
has a recommend capacity for the power supply unit of 2.5A which I assume to be close to the current the default power supply unit will provide.
Using all 150 LEDs (5m * 30LEDs/m) at the same time leads to a maximum of 9A which is definitely above 2.5A.
You can obviously bypass these problems with an external powersource for the LED strip but if you don't decide to use one be aware!
