# Video Display Setup

## Instalacja zależności

```bash
# Zainstaluj PyAV (FFmpeg wrapper) i NumPy
pip install av numpy

# Lub użyj requirements.txt
pip install -r requirements.txt
```

## Wymagania systemowe

### macOS
```bash
# Zainstaluj FFmpeg przez Homebrew
brew install ffmpeg
```

### Linux (Ubuntu/Debian)
```bash
sudo apt-get install libavcodec-dev libavformat-dev libavutil-dev libswscale-dev
```

### Windows
```bash
# Pobierz FFmpeg z https://ffmpeg.org/download.html
# Dodaj do PATH
```

## Uruchomienie z GUI

```bash
python main.py
```

## Funkcje

- ✅ **Real-time H264 decoding** - dekodowanie wideo w czasie rzeczywistym
- ✅ **QML Video Display** - wyświetlanie przez QQuickPaintedItem
- ✅ **Aspect ratio preservation** - zachowanie proporcji obrazu
- ✅ **Frame counter** - licznik ramek na żywo
- ✅ **Status indicators** - wskaźniki statusu połączenia

## Architektura

```
VideoData (H264) → VideoDecoder (PyAV) → QImage → VideoImageItem → QML
                                                                      ↓
                                                              VideoDisplay
```

## Troubleshooting

### "Cannot import av"
```bash
pip install av
```

### "FFmpeg not found"
```bash
# macOS
brew install ffmpeg

# Linux
sudo apt-get install ffmpeg
```

### Czarny ekran
- Sprawdź czy phone jest podłączony do dongla
- Upewnij się że CarPlay/AndroidAuto jest aktywny
- Sprawdź czy widzisz logi "Decoded frame #..."

### Niska wydajność
- H264 decoding jest CPU-intensive
- Dla lepszej wydajności użyj GPU acceleration (PyAV + CUDA/VAAPI)
