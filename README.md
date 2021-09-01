# LightOrgan
A light organ with raspotify and a WS2812B LED strip on a Raspberry Pi

The light organ is able to react to all sounds played as the user pi.
I use it in conjunction with a custom systemd service that is very closely modeled after the one provided by raspotify
to transform the Raspberry Pi into a Spotify player.

## Hardware requirements
1. A Raspberry Pi with Raspbian
1. A WS2812B LED strip or similar

## Guide
1. Clone the repo and install the python libraries in `requirements.txt`
1. Correctly set up the WS2812B LED strip
1. Play some music as the user pi
1. Enjoy your light organ by executing the correct command

### Step 1: Repo and Python setup
Clone the repository, setup a python virtual environment and install all the necessary packages with the following commands:
```bash
git clone https://github.com/BurningKarl/LightOrgan.git
cd LightOrgan
python3 -m venv venv
source venv/bin/activate
pip install llvmlite-0.37.0-cp37-cp37m-linux_armv7l.whl
pip install -r requirements.txt
```

The `source venv/bin/activate` command activates the newly created virtual environment in the `venv` folder so that `python` and `pip` use the correct executables.
It can be deactivated by `deactivate`.

The second to last command installs `llvmlite`, a dependency of the `librosa` library needed for audio analysis.
As the version on PyPI does not have Raspberry Pi support, I have included my self-compiled wheel here.
For reference, the guide to building llvmlite manually can be found at https://llvmlite.readthedocs.io/en/latest/admin-guide/install.html#building-manually.

### Step 2: WS2812 setup
I used https://github.com/jgarff/rpi_ws281x/blob/master/README.md to help me to set up my WS2812B LED strip. 
I decided to use the PCM method on GPIO 21 (pin 40), because 

> When using PCM you cannot use digital audio devices which use I2S since I2S uses the PCM hardware, but you can use analog audio.

and analog audio is enough for my purposes. 
This also has the advantage that it is very easy to setup: 

* Connect the ground of the LED strip to ground of the raspberry pi (e.g. pin 4)
* Connect the 5V of the LED strip to 5V of the raspberry pi (e.g. pin 6)
* Connect the dataline of the LED strip to pin 40

A useful map of all the pins on the Raspberry Pi can be found at https://pinout.xyz/#.
Once you connected all of the wires, the LEDs will not automatically turn on. 
You can test everything with `sudo venv/bin/python strandtest.py -c` and the first six LEDs will start to light up in various colors and patterns.
The reason I have set `LED_COUNT = 6` is that there is a limit to the number LEDs that you can use simultaneously with the Raspbery Pi as the only power source.
A single LED can use up to 60 mA of current and it depends on the type of Raspberry Pi what currents it allows.
According to [this sheet](https://www.raspberrypi.org/documentation/hardware/raspberrypi/power/README.md) my Raspberry Pi 3B
has a recommend capacity for the power supply unit of 2.5A which I assume to be close to the current the default power supply unit will provide.
Using all 150 LEDs (5m * 30LEDs/m) at the same time leads to a maximum of 9A which is definitely above 2.5A.
You can obviously bypass these problems with an external power supply for the LED strip but if you don't decide to use one, be aware!

### Step 3: Play music
Check your audio setup by playing some music as the user pi.
Execute `cvlc --play-and-exit example.mp3` using any audio file and it should be played back via HDMI or connected headphones.
To make sure the audio can be recorded by the light organ script, run `arecord -d 10 -f cd test.wav` while the music is playing (you may use `screen` to execute both commands at the same time) to record 10 seconds of CD quality sound and play it back via `aplay test.wav`.
This should play back the recorded audio, if there is only silence you need to do some troubleshooting.

### Step 4: Enjoy
The audio signal output of the Raspberry Pi for the user pi can only be captured as the user pi 
but at the same time to control the LED strip access to `/dev/mem` is needed which is only given to the root user.
I solved this problem by creating two different python scripts: 
One runs as the user pi and captures the audio stream (`audio_to_stdout.py`) and one runs as root and controls the LED strip (`stdin_to_led_strip.py`).
As the name of the scripts suggests, they communicate through stdin and stdout.
The stdout of one script needs to be directed to the stdin of the second script with piping on the command line.
To use the light organ run
```bash
python -u audio_to_stdout.py | sudo venv/bin/python stdin_to_led_strip.py
```
Note that the `-u` option forces python to not buffer the stdout stream. If omitted, the data is sent in chunks and the LED strip will not react in real time.

The `stdin_to_led_strip.py` contains multiple visualizers, select the one you want inside the `main` function.

## Playing music from an external source

It is often more convenient to control the music through an external device.
The following list contains guides to approaches I've tried so far.

### Raspotify
Using [Raspotify](https://github.com/dtcooper/raspotify) one can let the Raspberry Pi act as a spotify playback device (only available for Spotify Premium users).
First, set up Raspotify as explained in its readme including the "Play via Bluetooth Speaker" section.
Essentially, the "Play via Bluetooth Speaker" explains how to set up the systemd service as a user service such that the sound is played back as the user pi.
This also essential here, because the python script can only pick up those sounds.

After a successful setup, the Spotify device "raspotify (...)" should appear.
To test whether the sound output of the Spotify Device can be captured by ALSA use `arecord` and `aplay` as explained above.

### Bluetooth
If you have a spare bluetooth dongle, you can turn your Raspberry Pi into a bluetooth speaker.
I roughly followed the guide at https://github.com/jobpassion/raspberryPi/blob/master/BluetoothSpeaker.md but found that many steps were unnecessary, at least using the full installation of Raspbian.

First use `sudo nano /etc/bluetooth/main.conf` to edit the bluetooth configuration.
Here, we need to uncomment the line `#Class = 0x000100` and change it to `Class = 0x00041C`.
This is necessary so that the Raspberry Pi advertises itself as a device that can play audio.
Afterwards we need `sudo systemctl restart bluetooth.service` so that these changes are applied.

Because the pulseaudio settings are very sensible and already include the `module-bluetooth-discover` and `module-bluetooth-policy` modules, we only need to connect the external device (e.g. a smartphone) to the Raspberry Pi.

Execute `bluetoothctl` to gain access to the bluetooth console.
Use `power on` and `discoverable on` to make the Raspberry Pi discoverable and connect to it using your other device.
While the pairing should work without issues the connection will be dropped shortly after.
This is because the Raspberry Pi does not yet trust the other device.
During the pairing process a line of the form
```
[NEW] Device <MAC address> <device name>
```
should come up on the bluetoothctl console.
You now have the MAC address of your device and can confirm using `info <MAC>` (where `<MAC>` is the MAC address) that this device is already paired but neither trusted nor connected.
Copy the MAC address and execute `trust <MAC>` followed by `connect <MAC>` to trust your device and connect to it.

Now your second device will redirect all audio to the Raspberry Pi where the light organ script can pick it up.

## Troubleshooting

### The sound is choppy and the playback speed is too slow

This happens because of so-called underruns, i.e. when the audio buffer is not filled fast enough.
I have not yet figured out the exact cause, but I have observed that playback using `aplay` usually works fine, while the Spotify client often has this issue.
Sometimes stopping Spotify playback, executing `aplay example.wav` and unpausing Spotify afterwards fixes the issue.

### Numpy error
If you run into the error
```
libf77blas.so.3: cannot open shared object file: No such file or directory
```
when importing numpy (or executing a script which uses numpy), please refer to the explanations at https://numpy.org/devdocs/user/troubleshooting-importerror.html#raspberry-pi.
I used `sudo apt install libatlas-base-dev` to solve the issue.

