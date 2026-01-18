# Quick Start Guide

## What is PyCarPlay?

PyCarPlay is a widget component for embedding CarPlay in PyQt6 applications. Based on [react-carplay](https://github.com/rhysmorgan134/react-carplay), adapted for Python/Qt.

## 1. Installation

### Install System Dependencies

**macOS:**
```bash
brew install libusb
```

**Linux:**
```bash
sudo apt-get install libusb-1.0-0-dev
```

### Install PyCarPlay

```bash
pip install git+https://github.com/robixxxxx/pycarplay.git
```

## 2. Basic Embedding

Create `my_app.py`:

```python
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from pycarplay import CarPlayWidget

class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Create central widget with layout
        central = QWidget()
        layout = QVBoxLayout(central)
        
        # Add CarPlay widget
        carplay = CarPlayWidget()
        layout.addWidget(carplay)
        
        self.setCentralWidget(central)
        self.resize(1280, 720)

app = QApplication([])
window = MyApp()
window.show()
app.exec()
```

Run it:

```bash
python my_app.py
```

Done! The widget will auto-connect to your CarPlay dongle.

## 3. Add Control Buttons (5 minutes)

Add buttons to control CarPlay:

```python
from PySide6.QtWidgets import *
from pycarplay import CarPlayWidget

class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        central = QWidget()
        layout = QVBoxLayout(central)
        
        # Control buttons
        btn_layout = QHBoxLayout()
        
        connect_btn = QPushButton("Connect")
        connect_btn.clicked.connect(carplay.connect)  # <-- Connect to slot!
        btn_layout.addWidget(connect_btn)
        
        home_btn = QPushButton("Home")
        home_btn.clicked.connect(carplay.send_home)  # <-- Connect to slot!
        btn_layout.addWidget(home_btn)
        
        play_btn = QPushButton("Play/Pause")
        play_btn.clicked.connect(carplay.send_play_pause)  # <-- Connect to slot!
        btn_layout.addWidget(play_btn)
        
        layout.addLayout(btn_layout)
        
        # CarPlay widget
        carplay = CarPlayWidget()
        layout.addWidget(carplay)
        
        self.setCentralWidget(central)

app = QApplication([])
window = MyApp()
window.show()
app.exec()
```

## 4. Check Connection Status (2 minutes)

Monitor connection and get current info:

```python
# Check if connected
if carplay.is_connected():
    print("Dongle is connected")

if carplay.is_phone_connected():
    print("Phone is ready")
    carplay.send_home()  # Safe to send commands

# Get status text
status = carplay.get_status()
print(f"Status: {status}")

# Get current media info
song = carplay.get_current_song()
artist = carplay.get_current_artist()
if song:
    print(f"Playing: {song} - {artist}")
```

Example use in hardware button handler:

```python
def on_steering_wheel_button():
    # Check before sending command
    if carplay.is_phone_connected():
        carplay.send_play_pause()
    else:
        print("Phone not connected")
```

## 5. Listen to Events (3 minutes)

Connect to CarPlay signals:

```python
# In __init__:
carplay.phoneConnected.connect(self.on_phone_connected)
carplay.phoneDisconnected.connect(self.on_phone_disconnected)
carplay.dongleStatusChanged.connect(self.on_status_changed)
carplay.currentSongChanged.connect(self.on_song_changed)

def on_phone_connected(self):
    print("Phone connected!")
    self.setWindowTitle("CarPlay - Phone Connected")

def on_phone_disconnected(self):
    print("Phone disconnected")

def on_status_changed(self, status: str):
    self.status_label.setText(f"Status: {status}")

def on_song_changed(self, song: str):
    artist = carplay.get_current_artist()
    print(f"Now playing: {song} - {artist}")
```
```

## Available API Methods

### Status & Information

```python
carplay.is_connected()        # Returns bool: True if dongle connected
carplay.is_phone_connected()  # Returns bool: True if phone connected
carplay.get_status()          # Returns str: Status text
carplay.get_current_song()    # Returns str: Current song name
carplay.get_current_artist()  # Returns str: Current artist
```

### Signals (Events you can listen to)

```python
carplay.phoneConnected.connect(callback)           # Phone plugged in
carplay.phoneDisconnected.connect(callback)        # Phone unplugged
carplay.dongleStatusChanged.connect(callback)      # Status text changed
carplay.currentSongChanged.connect(callback)       # Song changed
carplay.currentArtistChanged.connect(callback)     # Artist changed
```

### Slots (Methods you can call from buttons)

```python
button.clicked.connect(carplay.connect)            # Connect to dongle
button.clicked.connect(carplay.disconnect)         # Disconnect
button.clicked.connect(carplay.send_home)          # Home button
button.clicked.connect(carplay.send_back)          # Back button
button.clicked.connect(carplay.send_play_pause)    # Play/Pause
button.clicked.connect(carplay.send_next_track)    # Next track
button.clicked.connect(carplay.send_previous_track) # Previous track
button.clicked.connect(carplay.toggle_audio)       # Mute/Unmute
button.clicked.connect(carplay.show_settings)      # Show settings

# Volume slider
slider.valueChanged.connect(lambda v: carplay.set_volume(v / 100.0))
```

## Complete Example

See `examples/embedded_widget.py` for a complete working example with:
- Connection buttons
- Navigation buttons (Home, Back)
- Media controls (Play, Next, Previous)
- Volume slider
- Status display
- Song info display

## Next Steps

- Run `examples/embedded_widget.py` to see all features
- Read full `README.md` for all signals and slots
- Customize configuration with `CarPlayConfig`
