import pathlib
import subprocess
import sys


def main():
    # The following is similar to the bash command
    #    python -u scripts/capture_audio.py | sudo python visualize.py
    #
    # The audio signal output of the Raspberry Pi for the user pi can only be captured
    # as the user pi, but at the same time to control the LED strip access to
    # `/dev/mem` is needed which is only given to the root user. The solution is to
    # split the two tasks up into two scripts: `capture_audio.py` and `visualize.py`.
    # The communication works by piping stdout of one to stdin of the other.
    #
    # The `-u` option forces python to not buffer the stdout stream. If omitted, the
    # data is sent in chunks and the LED strip will not react in real time.

    here = pathlib.Path(__file__).resolve().parent
    python = sys.executable

    visualize_process = subprocess.Popen(
        ["sudo", python, here / "visualize.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    )

    # Start capturing audio after initialization is done
    while visualize_process.stdout.readline() != b"INITIALIZED\n":
        pass

    capture_audio_process = subprocess.Popen(
        [python, "-u", here / "scripts" / "capture_audio.py"],
        stdout=visualize_process.stdin,
    )

    try:
        capture_audio_process.wait()
    except KeyboardInterrupt:
        # The processes handle Ctrl+C themselves
        pass


if __name__ == "__main__":
    main()
