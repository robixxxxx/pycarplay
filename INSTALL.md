# Installation Guide

## Install from GitHub

```bash
pip install git+https://github.com/robertburda/pycarplay.git
```

## Install from local repository

```bash
cd /path/to/pycarplay
pip install -e .
```

## Verify installation

```python
python -c "from pycarplay import CarPlayWidget, CarPlayConfig; print('✅ PyCarPlay installed successfully')"
```

## Requirements

All dependencies will be installed automatically:
- PySide6 >= 6.4.0
- pyusb >= 1.2.1
- opencv-python >= 4.8.0
- numpy >= 1.24.0
- pyaudio >= 0.2.13
- cryptography >= 41.0.0

## USB Permissions (Linux)

On Linux, you may need to add udev rules for USB access:

```bash
sudo sh -c 'echo "SUBSYSTEM==\"usb\", ATTR{idVendor}==\"1314\", ATTR{idProduct}==\"1520\", MODE=\"0666\"" > /etc/udev/rules.d/99-carplay.rules'
sudo udevadm control --reload-rules
```

## macOS Permissions

On macOS, you may need to grant USB permissions in System Preferences > Security & Privacy.
