# PyCarPlay Module - Project Summary

## 🎯 Co to jest PyCarPlay?

**PyCarPlay to widget Qt do embedowania w aplikacjach, NIE standalone aplikacja.**

Przeznaczony specjalnie do integracji z:
- 🔘 Fizycznymi przyciskami (GPIO, Arduino, Raspberry Pi)
- 🔌 Portami szeregowymi (UART, Serial)
- 🚗 Magistralami CAN
- 🎮 Niestandardowymi kontrolerami
- 🖥️ Systemami automotive/embedded

## 💡 Główna Idea

Widget dostarcza **czyste API** do wywoływania akcji CarPlay:

```python
carplay = CarPlayWidget()

# Wywołania bezpośrednie z hardware:
def on_physical_button_home():
    carplay.send_home()  # Bezpośrednie wywołanie!

def on_steering_wheel_next():
    carplay.send_next_track()  # Bezpośrednie wywołanie!
```

**Nie potrzebujesz Qt GUI** - możesz wywołać metody z:
- Przerwań GPIO
- Callbacków serial port
- Handlerów CAN bus
- Thread'ów sieciowych
- Dowolnego miejsca w kodzie!

## 📦 Struktura Modułu

```
pycarplay/
├── setup.py                    # Konfiguracja instalacji pip
├── pyproject.toml              # Nowoczesna konfiguracja pakietu
├── MANIFEST.in                 # Pliki do dołączenia w dystrybucji
├── README.md                   # Pełna dokumentacja
├── QUICKSTART.md               # Szybki start (5 min)
├── INSTALL.md                  # Instrukcje instalacji
│
├── examples/                   # Przykładowe aplikacje
│   ├── basic_usage.py         # Podstawowe użycie (standalone window)
│   ├── custom_config.py       # Niestandardowa konfiguracja
│   └── embedded_widget.py     # Widget w istniejącej aplikacji
│
└── src/
    └── pycarplay/             # Główny pakiet
        ├── __init__.py        # API: CarPlayWidget, CarPlayWindow, CarPlayConfig
        ├── version.py         # Wersja modułu
        ├── config.py          # System konfiguracji
        ├── widget.py          # CarPlayWidget i CarPlayWindow
        ├── controller.py      # VideoStreamController (logika)
        │
        ├── core/              # Rdzeń CarPlay
        │   ├── carplay_node.py
        │   ├── dongle_driver.py
        │   └── media_logger.py
        │
        ├── video/             # Obsługa video
        │   ├── video_decoder.py
        │   └── video_provider.py
        │
        ├── audio/             # Obsługa audio
        │   ├── audio_player.py
        │   └── microphone.py
        │
        ├── protocol/          # Protokół komunikacji
        │   ├── messages.py
        │   └── sendable.py
        │
        └── ui/                # Interfejs użytkownika
            ├── default/       # Domyślny UI
            │   └── Main.qml
            └── components/    # Komponenty QML
                ├── qmldir
                ├── CarPlayVideo.qml
                └── CarPlaySettings.qml
```

## 🎯 Główne Funkcje

### 1. **Modularność**
- Pełen pakiet Python instalowany przez `pip`
- Czyste API: `from pycarplay import CarPlayWidget, CarPlayConfig`
- Komponenty QML do ponownego użycia

### 2. **Konfiguracja**
```python
config = CarPlayConfig()
config.video.width = 1920
config.video.height = 1080
config.dongle.auto_connect = True
config.ui.custom_qml_path = "/path/to/my.qml"
```

### 3. **Łatwa Integracja**
```python
# Standalone
window = CarPlayWindow()

# Embedded
carplay = CarPlayWidget()
my_app.setCentralWidget(carplay)
```

### 4. **Customizacja UI**
- Domyślne komponenty QML (`CarPlayVideo`, `CarPlaySettings`)
- Możliwość zastąpienia własnym QML
- Import komponentów: `import PyCarPlay.Components`

## 📝 Klasy Konfiguracji

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
- Łączy wszystkie powyższe
- Metody: `from_dict()`, `from_json_file()`, `to_json_file()`

## 🔌 API Widgetów

### `CarPlayWidget(config, custom_qml_path, parent)`
- `connect_dongle()` - połącz ręcznie
- `disconnect_dongle()` - rozłącz
- `get_controller()` - dostęp do VideoStreamController
- `set_config(config)` - zmień konfigurację

### `CarPlayWindow(config, custom_qml_path)`
- Dziedziczy z `CarPlayWidget`
- Standalone window bez parenta

### `VideoStreamController`
Dostępny przez `widget.get_controller()`:
- **Signals**: `dongleStatusChanged`, `currentSongChanged`, `videoFrameReceived`
- **Methods**: `connectDongle()`, `setVolume()`, `sendKey()`

## 📦 Instalacja

```bash
# Z GitHub
pip install git+https://github.com/robertburda/pycarplay.git

# Lokalna (development)
pip install -e .
```

## 💡 Przykłady Użycia

### Minimal
```python
from pycarplay import CarPlayWindow
from PySide6.QtWidgets import QApplication

app = QApplication([])
CarPlayWindow().show()
app.exec()
```

### Custom Config
```python
config = CarPlayConfig()
config.video.width = 1920
window = CarPlayWindow(config=config)
```

### Embedded
```python
class MyApp(QMainWindow):
    def __init__(self):
        carplay = CarPlayWidget()
        self.setCentralWidget(carplay)
```

### Custom QML
```python
carplay = CarPlayWidget(custom_qml_path="my_ui.qml")
```

## 🎨 Komponenty QML

Dostępne do importu w custom QML:

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

## 🚀 Workflow Developera

1. **Instalacja dev**:
```bash
git clone https://github.com/robertburda/pycarplay.git
cd pycarplay
pip install -e ".[dev]"
```

2. **Testowanie**:
```bash
python examples/basic_usage.py
```

3. **Modyfikacja**:
- Edytuj pliki w `src/pycarplay/`
- Zmiany dostępne natychmiast (editable install)

4. **Budowanie**:
```bash
python -m build
```

## 📚 Dokumentacja

- **README.md** - Pełna dokumentacja z API reference
- **QUICKSTART.md** - Start w 5 minut
- **INSTALL.md** - Szczegóły instalacji
- **examples/** - Działające przykłady

## ✅ Co Zostało Zrobione

1. ✅ Setup.py i pyproject.toml dla instalacji pip
2. ✅ Rozdzielone komponenty QML (CarPlayVideo, CarPlaySettings)
3. ✅ System konfiguracji (CarPlayConfig z dataclasses)
4. ✅ CarPlayWidget i CarPlayWindow
5. ✅ Przykładowe aplikacje (3 przykłady)
6. ✅ Pełna dokumentacja (README, QUICKSTART, INSTALL)

## 🎯 Użycie

**Dla użytkowników końcowych:**
```bash
pip install git+https://github.com/robertburda/pycarplay.git
```

**Dla developerów:**
```bash
git clone ...
pip install -e ".[dev]"
```

**W aplikacji:**
```python
from pycarplay import CarPlayWidget, CarPlayConfig
```

---

**Moduł gotowy do publikacji i użycia!** 🎉
