from gpiozero import DigitalOutputDevice, Button
import subprocess
from time import sleep

# Configure rows, columns, and keypad layout
rows_pins = [15, 23, 24, 25]
cols_pins = [10, 22, 27, 17]
keys = ["1", "2", "3", "A",
        "4", "5", "6", "B",
        "7", "8", "9", "C",
        "*", "0", "#", "D"]

# Initialize row pins as DigitalOutputDevice
rows = [DigitalOutputDevice(pin) for pin in rows_pins]
# Initialize column pins as Buttons
cols = [Button(pin, pull_up=False) for pin in cols_pins]

def read_keypad():
    """
    Read the currently pressed keys on the keypad.
    :return: A list of pressed keys.
    """
    pressed_keys = []
    # Scan each row and column to identify pressed keys
    for i, row in enumerate(rows):
        row.on()  # Enable the current row
        for j, col in enumerate(cols):
            if col.is_pressed:  # Check if the column button is pressed
                # Calculate the key index based on row and column
                index = i * len(cols) + j
                pressed_keys.append(keys[index])
        row.off()  # Disable the current row
    return pressed_keys

# Main loop to continuously read the keypad and print newly pressed keys
last_key_pressed = []

print("Press keys on the keypad. Press Ctrl+C to exit.")
while True:
    pressed_keys = read_keypad()
    if pressed_keys and pressed_keys != last_key_pressed:
        print(pressed_keys)  # Print the list of pressed keys
        if "A" in pressed_keys:
            subprocess.check_output("systemctl --user start lightorgan.service", shell=True)
        elif "B" in pressed_keys:
            subprocess.check_output("systemctl --user start ledstrip_partylights.service", shell=True)
        elif "C" in pressed_keys:
            subprocess.check_output("systemctl --user start ledstrip_white.service", shell=True)
        elif "D" in pressed_keys:
            subprocess.check_output("systemctl --user start ledstrip_black.service", shell=True)
        elif "0" in pressed_keys:
            subprocess.check_output("sudo systemctl reboot", shell=True)
        last_key_pressed = pressed_keys
    sleep(0.1)  # Short delay to reduce CPU load
