# PyCarPlay Module - Project Structure

## Overview

PyCarPlay is an embeddable Qt widget for CarPlay integration in Python applications. Based on [react-carplay](https://github.com/rhysmorgan134/react-carplay) by Rhys Morgan, adapted for Python/Qt.

**Key Design Points:**
- Widget component (not standalone application)
- Protocol-agnostic (developer chooses vehicle communication method)
- Direct API for hardware integration (GPIO, serial, CAN, network)
- Configurable via dataclasses

## Basic Usage

```python
from pycarplay import CarPlayWidget

carplay = CarPlayWidget()

# Direct method calls from any source:
carplay.send_home()          # From GPIO interrupt
carplay.send_play_pause()    # From CAN message
carplay.send_next_track()    # From serial command
```

Methods can be called from:
- GPIO interrupts
- Serial port handlers
- CAN bus message callbacks
- Network API endpoints
- Any Python code

## Module Structure

```
pycarplay/
├── setup.py                    # Pip installation config
├── pyproject.toml              # Modern package config
├── MANIFEST.in                 # Distribution files
├── README.md                   # Full documentation
├── QUICKSTART.md               # Quick start guide
├── INSTALL.md                  # Installation instructions
├── CREDITS.md                  # Project credits
│
├── examples/                   # Example applications
│   ├── basic_usage.py         # Basic usage
│   ├── custom_config.py       # Custom configuration
│   ├── embedded_widget.py     # Widget in existing app
│   └── hardware_buttons.py    # Hardware integration examples
│
└── src/
    └── pycarplay/             # Main package
        ├── __init__.py        # API: CarPlayWidget, CarPlayConfig
        ├── version.py         # Module version
        ├── config.py          # Configuration system
        ├── widget.py          # CarPlayWidget class
        ├── controller.py      # VideoStreamController
        │
        ├── core/              # CarPlay core
        │   ├── carplay_node.py
        │   ├── dongle_driver.py
        │   └── media_logger.py
        │
        ├── video/             # Video handling
        │   ├── video_decoder.py
        │   └── video_provider.py
        │
        ├── audio/             # Audio handling
        │   ├── audio_player.py
        │   └── microphone.py
        │
        ├── protocol/          # Communication protocol
        │   ├── messages.py
        │   └── sendable.py
        │
        └── ui/                # User interface
            ├── default/       # Default UI
            │   └── Main.qml
            └── components/    # QML components
                ├── qmldir
                ├── CarPlayVideo.qml
                └── CarPlaySettings.qml
```

## Main Features

### 1. Modular Package
- Installable via `pip`
- Clean API: `from pycarplay import CarPlayWidget, CarPlayConfig`
- Reusable QML components

### 2. Configuration
```python
config = CarPlayConfig()
config.video.width = 1920
config.video.height = 1080
config.dongle.auto_connect = True
config.ui.custom_qml_path = "/path/to/my.qml"
```

### 3. Integration
```python
# Embedded widget
carplay = CarPlayWidget()
my_app.setCentralWidget(carplay)
```

### 4. UI Customization
- Default QML components (`CarPlayVideo`, `CarPlaySettings`)
- Custom QML support
- Import components: `import PyCarPlay.Components`

## Configuration Classes

### `VideoConfig`
- width, height, dpi, fps

### `AudioConfig`
- sample_rate, channels, chunk_size

### `DongleConfig`
- vendor_id, product_id
- auto_connect, reconnect_delay
- reconnect_max_attempts, decoder_error_delay

### `UIConfig`
- custom_qml_path, window_title
- background_color
- show_touch_indicator, show_media_info

### `CarPlayConfig`
- Combines all above
- Methods: `from_dict()`, `from_json_file()`, `to_json_file()`

## Widget API

### `CarPlayWidget(config, custom_qml_path, parent)`

**Status Methods:**
- `is_connected()` - Check if dongle connected
- `is_phone_connected()` - Check if phone connected
- `get_status()` - Get status string
- `get_current_song()` - Get current song
- `get_current_artist()` - Get current artist

**Control Methods:**
- `connect()` - Connect to dongle
- `disconnect()` - Disconnect
- `send_home()` - Home button
- `send_back()` - Back button
- `send_play_pause()` - Play/Pause
- `send_next_track()` - Next track
- `send_previous_track()` - Previous track
- `set_volume(float)` - Set volume 0.0-1.0
- `toggle_audio()` - Mute/unmute
- `show_settings()` - Show settings panel
- `hide_settings()` - Hide settings panel

**Signals:**
- `phoneConnected` - Phone plugged in
- `phoneDisconnected` - Phone unplugged
- `dongleStatusChanged(str)` - Status changed
- `currentSongChanged(str)` - Song changed
- `currentArtistChanged(str)` - Artist changed
- `videoFrameReceived(QImage)` - New video frame

**Advanced:**
- `get_controller()` - Access to VideoStreamController

## Installation

```bash
# From GitHub
pip install git+https://github.com/robixxxxx/pycarplay.git

# Local development
pip install -e .
```

## Usage Examples

### Basic
```python
from pycarplay import CarPlayWidget
from PySide6.QtWidgets import QApplication, QMainWindow

app = QApplication([])
window = QMainWindow()
carplay = CarPlayWidget()
window.setCentralWidget(carplay)
window.show()
app.exec()
```

### Custom Config
```python
config = CarPlayConfig()
config.video.width = 1920
config.video.height = 1080
carplay = CarPlayWidget(config=config)
```

### Hardware Integration
```python
carplay = CarPlayWidget()

# GPIO example
def on_gpio_button():
    if carplay.is_phone_connected():
        carplay.send_home()

# CAN bus example
def on_can_message(msg_id, data):
    if msg_id == 0x123:  # Steering wheel
        carplay.send_play_pause()
```

## QML Components

Available for import in custom QML:

```qml
import PyCarPlay.Components

CarPlayVideo {
    videoController: videoController
    showTouchIndicator: true
    showMediaInfo: true
    showNavigationInfo: true
}

CarPlaySettings {
    videoController: videoController
    onSettingsApplied: { /* handle */ }
}
```

## Development Workflow

1. **Install for development**:
```bash
git clone https://github.com/robixxxxx/pycarplay.git
cd pycarplay
pip install -e ".[dev]"
```

2. **Test**:
```bash
python examples/basic_usage.py
```

3. **Modify**:
- Edit files in `src/pycarplay/`
- Changes available immediately (editable install)

4. **Build**:
```bash
python -m build
```

## Documentation Files

- **README.md** - Full documentation with API reference
- **QUICKSTART.md** - Quick start guide
- **INSTALL.md** - Installation details
- **CREDITS.md** - Project credits
- **examples/** - Working examples

## Installation

**End users:**
```bash
pip install git+https://github.com/robixxxxx/pycarplay.git
```

**Developers:**
```bash
git clone https://github.com/robixxxxx/pycarplay.git
pip install -e ".[dev]"
```

**In application:**
```python
from pycarplay import CarPlayWidget, CarPlayConfig
```

## Credits

Based on [react-carplay](https://github.com/rhysmorgan134/react-carplay) by Rhys Morgan.
