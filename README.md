# LightOrgan
A light organ using a WS2812B LED strip on a Raspberry Pi

The light organ is able to react to all sounds played as the user pi. If the Raspberry Pi is set up as a Spotify playback device or a Bluetooth speaker (as explained below), you can easily control the music remotely.

## Hardware requirements
1. A Raspberry Pi with Raspberry Pi OS based on Debian Linux 12 (bookworm)
1. A WS2812B LED strip or similar

## Guide
1. Clone the repo and install the necessary python libraries
1. Correctly set up the WS2812B LED strip
1. Play some music as the user pi
1. Enjoy your light organ by executing the correct command

### Step 1: Repo and Python setup
This project uses [uv](https://docs.astral.sh/uv/) for dependency management, so it needs to be installed first, by following the steps at https://docs.astral.sh/uv/getting-started/installation/.
Executing `uv` in the shell should show information on its usage.

Afterwards, clone the repository, set up a python virtual environment and install all the necessary packages with the following commands:
```bash
git clone https://github.com/BurningKarl/LightOrgan.git
cd LightOrgan
sudo apt install libatlas-base-dev
uv sync
```

### Step 2: WS2812 setup
I used https://github.com/jgarff/rpi_ws281x/blob/master/README.md to help me to set up my WS2812B LED strip. 
I decided to use the PCM method on GPIO 21 (pin 40), because 

> When using PCM you cannot use digital audio devices which use I2S since I2S uses the PCM hardware, but you can use analog audio.

and analog audio is enough for my purposes. 
This also has the advantage that it is very easy to set up: 

* Connect the ground of the LED strip to ground of the Raspberry Pi (e.g. pin 6)
* Connect the 5V of the LED strip to 5V of the Raspberry Pi (e.g. pin 4)
* Connect the data line of the LED strip to pin 40

A useful map of all the pins on the Raspberry Pi can be found at https://pinout.xyz/#.
Once you connected all the wires, the LEDs will not automatically turn on. 
You can test everything with `sudo .venv/bin/python scripts/strandtest.py -c` and the first nine LEDs will start to light up in various colors and patterns.
The reason I have set `LED_COUNT = 9` is that there is a limit to the number LEDs that you can use simultaneously with the Raspberry Pi as the only power source.
A single LED can use up to 60 mA of current, and it depends on the type of Raspberry Pi what currents it allows.
According to [this sheet](https://www.raspberrypi.org/documentation/hardware/raspberrypi/power/README.md) my Raspberry Pi 3B
has a recommended capacity for the power supply unit of 2.5A which I assume to be close to the current the default power supply unit will provide.
Using all 150 LEDs (5 m * 30 LEDs/m) at the same time leads to a maximum of 9A which is definitely above 2.5A.
You can obviously bypass these problems with an external power supply for the LED strip but if you don't decide to use one, be aware!

### Step 3: Play music
Check your audio setup by playing some music as the user pi.
Execute `cvlc --play-and-exit example.mp3` using any audio file, and it should be played back via HDMI or connected headphones.
To make sure the audio can be recorded by the light organ script, run `arecord -d 10 -f cd test.wav` while the music is playing (you may use `screen` to execute both commands at the same time) to record 10 seconds of CD quality sound and play it back via `aplay test.wav`.
This should play back the recorded audio. If there is only silence, you need to do some troubleshooting.

### Step 4: Enjoy!
To use the light organ, run
```bash
uv run run.py
```

It starts capturing audio and visualizing it depending on the selected visualizer in `visualize.py`.
Without any changes 9 LEDs with rainbow colors will light up depending on the frequency decomposition of the currently playing audio.
LEDs closer to the start of the strip correspond to lower frequencies and those farther away correspond to higher frequencies (250 - 4000 Hz).

Some simple options such as the number of LEDs and the frequency of updates are exposed as command-line options (see `python run.py --help`).
Everything else can be changed by adapting the `visualize.py` script.

## Playing music from an external source

It is often more convenient to control the music through an external device.
The following list contains guides to approaches I've tried so far.

### Raspotify
Using [Raspotify](https://github.com/dtcooper/raspotify) one can let the Raspberry Pi act as a Spotify playback device (only available for Spotify Premium users).
First, set up Raspotify as explained in its README including the "Play via Bluetooth Speaker" section.
Essentially, the "Play via Bluetooth Speaker" explains how to set up the systemd service as a user service such that the sound is played back as the user pi.
This is essential here, because the python script can only pick up those sounds.

After a successful setup, the Spotify device "raspotify (...)" should appear.
To test whether the sound output of the Spotify Device can be captured by ALSA use `arecord` and `aplay` as explained above.

### Bluetooth
You can turn your Raspberry Pi into a Bluetooth speaker.
I roughly followed the guide at https://github.com/jobpassion/raspberryPi/blob/master/BluetoothSpeaker.md but found that many steps were unnecessary, at least using the full installation of Raspberry Pi OS.

First use `sudo nano /etc/bluetooth/main.conf` to edit the Bluetooth configuration.
Here, we need to uncomment the line `#Class = 0x000100` and change it to `Class = 0x00041C`.
This is necessary so that the Raspberry Pi advertises itself as a device that can play audio.
Afterwards we need `sudo systemctl restart bluetooth.service` so that these changes are applied.

Execute `bluetoothctl` to gain access to the Bluetooth console and then
```bluetoothctl
power on
discoverable on
agent KeyboardOnly
default-agent
```
to make the Raspberry Pi discoverable.
Next, connect to it using your other device.
The pairing should work without issues after confirming with "yes" on the bluetoothctl console and on the second device.
Potentially, you need to accept a request to authorize a service with a long ID on the console as well.

Now your second device will redirect all audio to the Raspberry Pi where the light organ script can pick it up.

## Running the light organ in the background

It is often useful to keep the program running in the background and take back control of the command-line.
To make this easier, I packaged it into a `systemd` user service.

```bash
mkdir --parents ~/.config/systemd/user/
cp lightorgan.service ~/.config/systemd/user/ 
systemctl --user daemon-reload
systemctl --user edit --full lightorgan.service
```
This will make the service file available to `systemd` and then open the file in an editor.
Make sure to change `PROJECT_ROOT` to the current folder (i.e. where `run.py` can be found), save your changes and close the editor.

Now, you can control the light organ with the following commands:
```bash
systemctl --user start lightorgan.service   # Start the light organ
systemctl --user stop lightorgan.service    # Stop the light organ
systemctl --user restart lightorgan.service # Restart the light organ
systemctl --user status lightorgan.service  # Check if the light organ is running
```


## Troubleshooting

### NumPy error
If you run into the error
```
libf77blas.so.3: cannot open shared object file: No such file or directory
```
when importing NumPy (or executing a script which uses NumPy), please refer to the explanations at https://numpy.org/devdocs/user/troubleshooting-importerror.html#raspberry-pi.
I used `sudo apt install libatlas-base-dev` to solve the issue.

