# Installation Guide

## Prerequisites

### 1. Install System Dependencies

**macOS:**
```bash
brew install libusb
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install libusb-1.0-0-dev libegl1 libgl1 libglx-mesa0 libfontconfig1 libqt5gui5 libqt5qml5 libqt5quick5 libpulse0 libpulse-mainloop-glib0 qml6-module-qtmultimedia qt6-multimedia-dev libqt6multimedia6 libqt6multimediaquick6 libpulse0 libegl1 libgl1 lib fontconfig1 libgbm-dev libdrm-dev libegl1-mesa-dev libgles2-mesa-dev libxkbcommon-dev libinput-dev
```

**Linux (Fedora/RHEL):**
```bash
sudo dnf install libusb-devel
```

### 2. Install PyCarPlay

**From GitHub:**
```bash
pip install git+https://github.com/robixxxxx/pycarplay.git
```

**From local repository:**
```bash
cd /path/to/pycarplay
pip install -e .
```

## Verify Installation

```python
python -c "from pycarplay import CarPlayWidget, CarPlayConfig; print('PyCarPlay installed successfully')"
```

## Python Dependencies

Installed automatically:
- PySide6 >= 6.4.0
- pyusb >= 1.2.1
- opencv-python >= 4.8.0
- numpy >= 1.24.0
- sounddevice >= 0.4.6
- cryptography >= 41.0.0

## USB Permissions (Linux)

On Linux, you may need to add udev rules for USB access:

```bash
sudo sh -c 'echo "SUBSYSTEM==\"usb\", ATTR{idVendor}==\"1314\", ATTR{idProduct}==\"1520\", MODE=\"0666\"" > /etc/udev/rules.d/99-carplay.rules'
sudo udevadm control --reload-rules
```

## macOS Permissions

On macOS, you may need to grant USB permissions in System Preferences > Security & Privacy.

## Running the Application
```bash
QT_QPA_PLATFORM=linuxfb python examples/basic_usage.py
```
