# PyCarPlay-Qt

🚗 **CarPlay Widget for PyQt6 Applications**

Python widget component for embedding CarPlay in PyQt6 apps. Designed for integration with physical hardware buttons, GPIO, serial controls, and custom input devices.

## Key Features

- ✅ **Embeddable Widget** - Component for your PyQt6 app
- ✅ **Hardware Button Support** - Direct API calls for GPIO, serial, CAN bus
- ✅ **Signal/Slot API** - Full Qt integration
- ✅ CarPlay protocol via USB dongle
- 🎥 H.264 video decoding
- 🔊 Audio playback with volume control
- 📱 Touch and keyboard input

## Installation

```bash
pip install git+https://github.com/robertburda/pycarplay.git
```

## Quick Start - Basic Embedding

```python
from PySide6.QtWidgets import *
from pycarplay import CarPlayWidget

class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        central = QWidget()
        layout = QVBoxLayout(central)
        
        # Add CarPlay widget
        carplay = CarPlayWidget()
        layout.addWidget(carplay)
        
        self.setCentralWidget(central)

app = QApplication([])
window = MyApp()
window.show()
app.exec()
```

## Hardware Buttons Integration

**Perfect for car systems, custom devices, Raspberry Pi, Arduino, etc.**

All methods can be called directly - no GUI required:

```python
# Create widget
carplay = CarPlayWidget()

# Physical button handlers - call directly!
def on_steering_wheel_home():
    carplay.send_home()

def on_steering_wheel_back():
    carplay.send_back()

def on_steering_wheel_play():
    carplay.send_play_pause()

def on_volume_knob_turned(value):
    carplay.set_volume(value / 100.0)
```

### Raspberry Pi GPIO Example

```python
import RPi.GPIO as GPIO

carplay = CarPlayWidget()

# Setup GPIO pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Home button
GPIO.setup(27, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Back button

# Connect physical buttons to CarPlay
GPIO.add_event_detect(17, GPIO.FALLING, 
                     callback=lambda x: carplay.send_home(),
                     bouncetime=200)

GPIO.add_event_detect(27, GPIO.FALLING,
                     callback=lambda x: carplay.send_back(),
                     bouncetime=200)
```

### Serial Port / CAN Bus Example

```python
import serial

carplay = CarPlayWidget()
ser = serial.Serial('/dev/ttyUSB0', 9600)

while True:
    command = ser.readline().decode().strip()
    
    # Map commands to CarPlay actions
    if command == 'HOME':
        carplay.send_home()
    elif command == 'BACK':
        carplay.send_back()
    elif command == 'PLAY':
        carplay.send_play_pause()
    elif command == 'NEXT':
        carplay.send_next_track()
    elif command.startswith('VOL:'):
        volume = int(command.split(':')[1]) / 100.0
        carplay.set_volume(volume)
```

## Available API Methods

### Status & Information

```python
carplay.is_connected()        # Returns bool: True if dongle connected
carplay.is_phone_connected()  # Returns bool: True if phone connected
carplay.get_status()          # Returns str: "Connected - iPhone", etc.
carplay.get_current_song()    # Returns str: Currently playing song
carplay.get_current_artist()  # Returns str: Current artist name
```

Example usage:
```python
# Check connection before sending commands
if carplay.is_phone_connected():
    carplay.send_play_pause()
    
# Monitor status
status = carplay.get_status()
print(f"CarPlay Status: {status}")
```

### Navigation & Control

```python
carplay.send_home()           # Home button
carplay.send_back()           # Back button
carplay.send_play_pause()     # Play/Pause media
carplay.send_next_track()     # Next track
carplay.send_previous_track() # Previous track
```

### Connection

```python
carplay.connect()      # Connect to dongle
carplay.disconnect()   # Disconnect
```

### Audio

```python
carplay.set_volume(0.8)   # Set volume 0.0-1.0
carplay.toggle_audio()    # Mute/Unmute
```

### Advanced (via controller)

```python
controller = carplay.get_controller()
controller.sendKey("up")      # D-pad up
controller.sendKey("down")    # D-pad down
controller.sendKey("left")    # D-pad left
controller.sendKey("right")   # D-pad right
controller.sendKey("select")  # OK/Enter
```

## Available Signals (Events)

Listen to CarPlay events:

```python
carplay.phoneConnected.connect(callback)        # Phone plugged in
carplay.phoneDisconnected.connect(callback)     # Phone unplugged
carplay.dongleStatusChanged.connect(callback)   # Status changed
carplay.currentSongChanged.connect(callback)    # Song changed
carplay.currentArtistChanged.connect(callback)  # Artist changed
```

## Configuration

```python
from pycarplay import CarPlayConfig

config = CarPlayConfig()
config.video.width = 1920
config.video.height = 1080
config.dongle.auto_connect = False  # Manual control

carplay = CarPlayWidget(config=config)
```

## Examples

- `examples/hardware_buttons.py` - Physical button integration (GPIO, serial, CAN)
- `examples/basic_usage.py` - Simple embedding
- `examples/embedded_widget.py` - Full GUI with controls
- `examples/custom_config.py` - Configuration

## Requirements

- Python >= 3.9
- PySide6 >= 6.4.0
- Compatible CarPlay USB dongle

## License

MIT License

---

**Perfect for automotive, embedded systems, and custom hardware projects!** 🚗
