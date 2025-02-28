# Python Keystock

## Overview

Python Keystock is a project that captures and displays keyboard and mouse input events in real-time. It uses `evdev` for capturing input events and `websockets` for broadcasting these events to a web client. This can be used with OBS (Open Broadcaster Software) to display input events during live streams or recordings.

## Requirements

To install the required dependencies, run:
```sh
pip install -r requirements.txt
```

## Usage

1. **Run the server:**
    ```sh
    sudo python3 main.py
    ```
    Note: The script needs to be run with root privileges to access input devices.

2. **Open the HTML file:**
    Open `input-history-windows.html` in a browser to see the input events displayed in real-time.

3. **Add to OBS:**
    In OBS, add a new "Browser" source and set the URL to the local address where the HTML file is served. Adjust the width and height as needed.

## Files

- `main.py`: The main server script that captures input events and broadcasts them via WebSocket.
- `input-history-windows.html`: The HTML file that displays the input events.
- `requirements.txt`: Lists the Python dependencies.
- `.gitignore`: Specifies files and directories to be ignored by git.

## License

This project is licensed under the MIT License.

## Acknowledgements

- [evdev](https://python-evdev.readthedocs.io/en/latest/)
- [pynput](https://pynput.readthedocs.io/en/latest/)
- [python-xlib](https://github.com/python-xlib/python-xlib)
- [websockets](https://websockets.readthedocs.io/en/stable/)
- [libuiohook](https://github.com/kwhat/libuiohook)
- [Font Awesome](https://fontawesome.com/)

## Inspiration

This project was inspired by [Christian Kyle Ching](https://github.com/christiankyle-ching/).
