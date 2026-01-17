# PyCarPlay - Quick Start Guide

## 🚀 Szybki start (5 minut)

### Krok 1: Instalacja

```bash
# Zainstaluj Python packages
pip install PySide6 pyusb

# Zainstaluj libusb
# macOS:
brew install libusb

# Linux (Ubuntu/Debian):
sudo apt-get install libusb-1.0-0-dev

# Linux (Fedora):
sudo dnf install libusb-devel
```

### Krok 2: Uprawnienia USB (tylko Linux)

```bash
# Stwórz plik reguł udev
sudo nano /etc/udev/rules.d/99-carplay.rules

# Dodaj te linie:
SUBSYSTEM=="usb", ATTRS{idVendor}=="1314", ATTRS{idProduct}=="1520", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="1314", ATTRS{idProduct}=="1521", MODE="0666", GROUP="plugdev"

# Przeładuj reguły
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### Krok 3: Uruchomienie

#### Opcja A: Przykład z konsolą (najprostsze)

```bash
python example.py
```

To pokaże wszystkie otrzymywane dane w konsoli:
- 📱 Status połączenia telefonu
- 📹 Video frames (H264)
- 🔊 Audio packets (PCM)
- 🎵 Metadata muzyki
- ⌨️  Komendy od systemu

#### Opcja B: GUI (pełna aplikacja)

```bash
python main.py
```

Kliknij "Connect USB" i gotowe!

#### Opcja C: Własny kod

```python
from carplay_node import CarplayNode, MessageType
from dongle_driver import DongleConfig

carplay = CarplayNode(DongleConfig())

def on_msg(msg):
    if msg.msg_type == MessageType.VIDEO:
        print(f"Video: {msg.message.width}x{msg.message.height}")

carplay.onmessage = on_msg
carplay.start()

import time
while True:
    time.sleep(1)
```

## 🔍 Testowanie

### Test 1: Protokół komunikacji
```bash
python test_messages.py
```
Powinno pokazać: `All tests passed! ✓`

### Test 2: USB connection (bez GUI)
```bash
python dongle_driver.py
```
Powinno:
1. Znaleźć urządzenie USB
2. Inicjalizować połączenie
3. Wysłać heartbeat co 2 sekundy

### Test 3: CarPlay node
```bash
python carplay_node.py
```
Pełny test z automatycznym parowaniem WiFi.

## 📱 Jak używać z telefonem

### iPhone (CarPlay)
1. Podłącz dongle USB do komputera
2. Uruchom: `python example.py`
3. Podłącz iPhone kablem Lightning do dongla
4. iPhone powinien automatycznie uruchomić CarPlay
5. Obserwuj logi w konsoli!

### Android (Android Auto)
1. Podłącz dongle USB do komputera
2. Uruchom: `python example.py`
3. Podłącz telefon Android kablem USB-C do dongla
4. Włącz Android Auto na telefonie
5. Telefon połączy się przez WiFi
6. Obserwuj logi w konsoli!

## 🎯 Co zobaczysz

### Pierwsze połączenie:
```
Looking for USB device...
Found device: <Device ...>
Initializing dongle driver...
Sending initialization messages
Starting read loop
Starting heartbeat loop
Driver started
Setting up pair timeout...

📱 Phone connected: CarPlay
   WiFi available: Yes

📹 Video: 1280x720, 12453 bytes, flags=0x1, frame #30
🔊 Audio: 1920 samples, volume=0.75, packet #100
```

### Podczas odtwarzania muzyki:
```
🎵 Now playing:
   Song: Bohemian Rhapsody
   Artist: Queen
   Album: A Night at the Opera
   App: Music

🎨 Album cover received (base64)
```

## 🐛 Rozwiązywanie problemów

### "No compatible device found"
```bash
# Sprawdź czy dongle jest widoczny
# macOS:
system_profiler SPUSBDataType | grep -A 10 1314

# Linux:
lsusb | grep 1314
```

### "Permission denied" (Linux)
```bash
# Sprawdź czy użytkownik jest w grupie plugdev
groups

# Jeśli nie ma 'plugdev', dodaj:
sudo usermod -a -G plugdev $USER

# Wyloguj się i zaloguj ponownie
```

### Dongle się łączy ale nie ma video/audio
- To normalne! Video wymaga dekodera H264 (FFmpeg/GStreamer)
- Audio wymaga odtwarzacza PCM (PyAudio)
- Na razie pokazujemy tylko RAW dane w logach

## 📚 Więcej informacji

- **README.md** - Pełna dokumentacja
- **VERIFICATION.md** - Szczegóły implementacji vs TypeScript
- **USB_GUIDE.md** - Szczegóły protokołu USB

## 🎉 Gotowe!

Teraz masz działającą komunikację z donglem CarPlay/AndroidAuto!

Następne kroki:
1. Implementacja dekodera H264 dla video
2. Implementacja odtwarzacza PCM dla audio
3. Implementacja obsługi touch events
4. Stworzenie pełnego GUI

Happy coding! 🚗💨
