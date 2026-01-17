# PyCarPlay - Video Stream Player

Aplikacja PySide6 z interfejsem QML do wyświetlania transmisji wideo z dongla CarPlay/AndroidAuto przez USB.

**📖 [Quick Start Guide](QUICKSTART.md)** - Zacznij w 5 minut!

**🔍 [Verification](VERIFICATION.md)** - Analiza zgodności z TypeScript

## Funkcje

- ✅ **Komunikacja USB** z donglem CarPlay/AndroidAuto
- ✅ **Odtwarzanie plików wideo** (MP4, AVI, MKV, MOV, etc.)
- ✅ **Obsługa strumieni sieciowych** (HTTP, RTSP, HLS)
- ✅ **Protokół komunikacji** - pełna implementacja protokołu dongla
- ✅ **Kontrola odtwarzania** (Play, Pauza, Stop)
- ✅ **Regulacja głośności**
- ✅ **Pasek postępu** z możliwością przewijania
- ✅ **Nowoczesny interfejs** użytkownika w ciemnym motywie

## Struktura projektu

```
pycarplay/
├── main.py                 # Główna aplikacja PySide6/QML
├── main.qml               # Interfejs użytkownika QML
├── carplay_node.py        # High-level API (zgodne z carplay.ts)
├── dongle_driver.py       # Driver USB dla dongla
├── messages.py            # Klasy wiadomości przychodzących
├── sendable.py            # Klasy wiadomości wychodzących
├── test_messages.py       # Testy protokołu
├── requirements.txt       # Zależności Python
├── README.md             # Ten plik
└── VERIFICATION.md       # Weryfikacja zgodności z TypeScript
```

## Instalacja

### 1. Zainstaluj wymagane pakiety Python

```bash
pip install -r requirements.txt
```

### 2. Zainstaluj libusb (wymagane dla PyUSB)

**macOS:**
```bash
brew install libusb
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install libusb-1.0-0-dev
```

**Linux (Fedora):**
```bash
sudo dnf install libusb-devel
```

### 3. Uprawnienia USB (tylko Linux)

Na Linuxie potrzebujesz dodać reguły udev:

```bash
sudo nano /etc/udev/rules.d/99-carplay.rules
```

Dodaj:
```
SUBSYSTEM=="usb", ATTRS{idVendor}=="1314", ATTRS{idProduct}=="1520", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="1314", ATTRS{idProduct}=="1521", MODE="0666", GROUP="plugdev"
```

Następnie przeładuj reguły:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## Uruchomienie

### Aplikacja GUI

```bash
python main.py
```

### Test komunikacji USB (bez GUI)

```bash
python dongle_driver.py
```

### Testy protokołu

```bash
python test_messages.py
```

## Użycie

### Połączenie z donglem USB

#### Metoda 1: GUI (Zalecane dla użytkowników)

1. Podłącz dongle USB CarPlay/AndroidAuto
2. Uruchom aplikację: `python main.py`
3. Kliknij przycisk **"Connect USB"**
4. Status połączenia pojawi się w nagłówku (zielony = połączono)
5. Podłącz iPhone lub telefon Android do dongla
6. Interfejs CarPlay/AndroidAuto pojawi się automatycznie

#### Metoda 2: High-level API (Zalecane dla developerów)

```python
from carplay_node import CarplayNode, CarplayMessage, MessageType
from dongle_driver import DongleConfig, HandDriveType

# Konfiguracja
config = DongleConfig(
    width=1280,
    height=720,
    fps=30,
    dpi=160,
    box_name="pyCarPlay",
    hand=HandDriveType.LHD,
    wifi_type="5ghz",
    mic_type="os"
)

# Stwórz node
carplay = CarplayNode(config)

# Callback dla wiadomości
def on_message(msg: CarplayMessage):
    if msg.msg_type == MessageType.VIDEO:
        print(f"Video frame: {msg.message.width}x{msg.message.height}")
        # Decode and display video
    elif msg.msg_type == MessageType.AUDIO:
        print(f"Audio data: {len(msg.message.data)} samples")
        # Play audio
    elif msg.msg_type == MessageType.PLUGGED:
        print(f"Phone connected: {msg.message.phone_type.name}")

carplay.onmessage = on_message

# Start
carplay.start()

# Keep running
import time
while True:
    time.sleep(1)
```

#### Metoda 3: Low-level API (Dla zaawansowanych)

```python
from dongle_driver import DongleDriver, DongleConfig

driver = DongleDriver()

def on_message(message):
    print(f"Message: {message.header.type.name}")

driver.on_message(on_message)
driver.initialise()
driver.start(DongleConfig())
```

### Odtwarzanie pliku wideo

1. Kliknij **"Wybierz plik"**
2. Wybierz plik wideo z dysku
3. Kliknij **"Play"**

### Odtwarzanie strumienia

1. Wprowadź URL w polu "URL/Ścieżka" (np. `http://example.com/stream.m3u8`)
2. Kliknij **"Załaduj"**
3. Kliknij **"Play"**

## Protokół komunikacji

### Obsługiwane urządzenia USB

- Vendor ID: `0x1314`, Product ID: `0x1520`
- Vendor ID: `0x1314`, Product ID: `0x1521`

### Format wiadomości

Każda wiadomość składa się z:
- **Nagłówek** (16 bajtów):
  - Magic number: `0x55aa55aa` (4 bajty)
  - Długość payload: uint32 (4 bajty)
  - Typ wiadomości: uint32 (4 bajty)
  - Type check: `~typ & 0xFFFFFFFF` (4 bajty)
- **Payload** (zmienna długość)

### Typy wiadomości przychodzących

- `VideoData (0x06)` - Ramki wideo H264
- `AudioData (0x07)` - Dane audio PCM
- `Plugged (0x02)` - Telefon podłączony
- `Unplugged (0x04)` - Telefon odłączony
- `Opened (0x01)` - Połączenie nawiązane
- `Command (0x08)` - Komendy od telefonu
- `MediaData (0x2a)` - Metadane mediów
- I wiele innych...

### Typy wiadomości wychodzących

- `Open (0x01)` - Inicjalizacja połączenia
- `HeartBeat (0xaa)` - Utrzymanie połączenia
- `Command (0x08)` - Wysyłanie komend
- `Touch (0x05)` - Zdarzenia dotykowe
- `MultiTouch (0x17)` - Zdarzenia multi-touch
- `SendFile (0x99)` - Wysyłanie plików/konfiguracji

## Konfiguracja dongla

Możesz dostosować konfigurację edytując `DongleConfig` w `main.py`:

```python
config = DongleConfig(
    width=1280,               # Rozdzielczość pozioma
    height=720,               # Rozdzielczość pionowa
    fps=30,                   # Klatki na sekundę
    dpi=160,                  # DPI ekranu
    format=5,                 # Format wideo (5 = H264)
    ibox_version=2,           # Wersja protokołu iBox
    phone_work_mode=2,        # Tryb pracy telefonu
    packet_max=49152,         # Maksymalny rozmiar pakietu
    box_name="pyCarPlay",     # Nazwa urządzenia
    night_mode=False,         # Tryb nocny
    hand=HandDriveType.LHD,   # Kierownica po lewej/prawej
    media_delay=300,          # Opóźnienie mediów (ms)
    audio_transfer_mode=False,# Transfer audio przez dongle
    wifi_type="5ghz",         # "5ghz" lub "2.4ghz"
    mic_type="os"             # "os" lub "box"
)
```

## Architektura

```
┌─────────────┐
│   main.py   │  ← GUI (PySide6 + QML)
└──────┬──────┘
       │
       ├─────► main.qml (Interfejs użytkownika)
       │
       └─────► dongle_driver.py
                    │
                    ├─────► messages.py (Parsowanie wiadomości)
                    │
                    ├─────► sendable.py (Wysyłanie wiadomości)
                    │
                    └─────► USB Device (pyusb)
                                │
                                ↓
                         [ Dongle CarPlay ]
                                │
                                ↓ WiFi/Bluetooth
                         [ iPhone/Android ]
```

## Debugowanie

### Włącz verbose logging

Driver automatycznie loguje wszystkie operacje do konsoli:
- Inicjalizację urządzenia
- Wysyłane wiadomości
- Otrzymane wiadomości
- Błędy komunikacji

### Testowanie protokołu

```bash
python test_messages.py
```

To uruchomi testy serializacji/deserializacji wiadomości.

### Bezpośredni test USB

```bash
python dongle_driver.py
```

To uruchomi driver w trybie standalone (bez GUI) i wyświetli wszystkie otrzymywane wiadomości.

## Rozwiązywanie problemów

### "No compatible device found"

- Sprawdź czy dongle jest podłączony: `lsusb` (Linux) lub `system_profiler SPUSBDataType` (macOS)
- Sprawdź uprawnienia USB (Linux)
- Sprawdź czy libusb jest zainstalowany

### "Could not open device"

- Na Linuxie: dodaj reguły udev (zobacz sekcję Instalacja)
- Na macOS: może być potrzebny restart po instalacji libusb

### Brak video/audio

- Protokół jest poprawnie zaimplementowany ale wymaga dekodowania:
  - Video: H264 (wymaga FFmpeg/GStreamer)
  - Audio: PCM S16LE (wymaga obsługi audio)

## Następne kroki (TODO)

- [ ] Dekodowanie video H264 z VideoData
- [ ] Wyświetlanie video w QML VideoOutput
- [ ] Odtwarzanie audio PCM
- [ ] Obsługa zdarzeń dotykowych (Touch/MultiTouch)
- [ ] Obsługa klawiszy sterujących
- [ ] Wyświetlanie metadanych mediów (Media Data)
- [ ] Integracja z GStreamer dla hardware decoding

## Wymagania systemowe

- Python 3.8+
- PySide6 >= 6.6.0
- pyusb >= 1.2.1
- libusb (systemowa biblioteka)
- Kodeki wideo/audio (dla pełnej funkcjonalności)

## Licencja

Ten projekt jest stworzony na podstawie protokołu z projektu nodePlay.

## Autorzy

- Implementacja Python/PySide6: PyCarPlay
- Protokół bazowany na: nodePlay (TypeScript)
